#!/usr/bin/env python3
"""
Binance Futures Testnet Trading Bot — CLI entry point.

Usage examples:
  # Market buy
  python cli.py place --symbol BTCUSDT --side BUY --type MARKET --qty 0.001

  # Limit sell
  python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --qty 0.001 --price 70000

  # Stop-Market sell (bonus order type)
  python cli.py place --symbol ETHUSDT --side SELL --type STOP_MARKET --qty 0.01 --stop-price 3000

  # List open orders
  python cli.py orders --symbol BTCUSDT

  # Cancel an order
  python cli.py cancel --symbol BTCUSDT --order-id 123456789
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from dotenv import load_dotenv

from bot.client import BinanceFuturesClient, BinanceAPIError
from bot.logging_config import setup_logging, get_logger
from bot.orders import place_order

# Bootstrap
load_dotenv()
logger = setup_logging(os.getenv("LOG_LEVEL", "INFO"))
log = get_logger("cli")


def _build_client() -> BinanceFuturesClient:
    api_key = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()
    if not api_key or not api_secret:
        print(
            "\n[ERROR] BINANCE_API_KEY and BINANCE_API_SECRET must be set.\n"
            "        Copy .env.example to .env and fill in your testnet credentials.\n"
        )
        sys.exit(1)
    return BinanceFuturesClient(api_key=api_key, api_secret=api_secret)


def _print_json(data):
    print(json.dumps(data, indent=2))


def cmd_place(args):
    client = _build_client()
    print("\n" + "─" * 50)
    print("  ORDER REQUEST SUMMARY")
    print("─" * 50)
    print(f"  Symbol     : {args.symbol.upper()}")
    print(f"  Side       : {args.side.upper()}")
    print(f"  Type       : {args.type.upper()}")
    print(f"  Quantity   : {args.qty}")
    if args.price:
        print(f"  Price      : {args.price}")
    if args.stop_price:
        print(f"  Stop Price : {args.stop_price}")
    print("─" * 50 + "\n")

    log.info(
        "CLI place order | symbol=%s side=%s type=%s qty=%s price=%s stopPrice=%s",
        args.symbol, args.side, args.type, args.qty, args.price, args.stop_price,
    )

    result = place_order(
        client=client,
        symbol=args.symbol,
        side=args.side,
        order_type=args.type,
        quantity=args.qty,
        price=args.price,
        stop_price=args.stop_price,
        time_in_force=args.tif,
    )

    print(result.summary())
    print()

    if args.json and result.raw:
        print("Raw API response:")
        _print_json(result.raw)

    sys.exit(0 if result.success else 1)


def cmd_orders(args):
    client = _build_client()
    try:
        orders = client.get_open_orders(symbol=args.symbol)
    except BinanceAPIError as exc:
        print(f"\n[ERROR] {exc}\n")
        sys.exit(1)
    except Exception as exc:
        print(f"\n[ERROR] Unexpected error: {exc}\n")
        sys.exit(1)

    if not orders:
        print("\nNo open orders found.\n")
        return

    print(f"\nOpen orders ({len(orders)}):")
    print("─" * 60)
    for o in orders:
        print(
            f"  {o.get('orderId'):<15} {o.get('symbol'):<12} "
            f"{o.get('side'):<5} {o.get('type'):<12} "
            f"qty={o.get('origQty')} price={o.get('price')} status={o.get('status')}"
        )
    print("─" * 60 + "\n")
    if args.json:
        _print_json(orders)


def cmd_cancel(args):
    client = _build_client()
    print(f"\nCancelling order {args.order_id} for {args.symbol.upper()} ...")
    try:
        result = client.cancel_order(symbol=args.symbol.upper(), order_id=args.order_id)
        print(f"✓  Cancelled | orderId={result.get('orderId')} status={result.get('status')}\n")
        if args.json:
            _print_json(result)
    except BinanceAPIError as exc:
        print(f"\n[ERROR] {exc}\n")
        sys.exit(1)
    except Exception as exc:
        print(f"\n[ERROR] Unexpected error: {exc}\n")
        sys.exit(1)


def cmd_account(args):
    client = _build_client()
    try:
        info = client.get_account()
    except BinanceAPIError as exc:
        print(f"\n[ERROR] {exc}\n")
        sys.exit(1)

    balances = [b for b in info.get("assets", []) if float(b.get("walletBalance", 0)) > 0]
    print("\nAccount balances (non-zero):")
    print("─" * 50)
    for b in balances:
        print(
            f"  {b['asset']:<8} wallet={b['walletBalance']:<15} "
            f"unrealisedPnl={b.get('unrealizedProfit', '0')}"
        )
    print("─" * 50 + "\n")
    if args.json:
        _print_json(info)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description="Binance Futures Testnet Trading Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Console log verbosity (default: INFO)",
    )
    parser.add_argument("--json", action="store_true", help="Print raw API response as JSON")

    sub = parser.add_subparsers(dest="command", required=True)

    place = sub.add_parser("place", help="Place a new futures order")
    place.add_argument("--symbol", required=True)
    place.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"])
    place.add_argument(
        "--type", required=True,
        choices=["MARKET", "LIMIT", "STOP_MARKET", "market", "limit", "stop_market"],
    )
    place.add_argument("--qty", required=True, type=float)
    place.add_argument("--price", type=float, default=None)
    place.add_argument("--stop-price", dest="stop_price", type=float, default=None)
    place.add_argument("--tif", default="GTC", choices=["GTC", "IOC", "FOK"])
    place.set_defaults(func=cmd_place)

    orders_cmd = sub.add_parser("orders", help="List open orders")
    orders_cmd.add_argument("--symbol", default=None)
    orders_cmd.set_defaults(func=cmd_orders)

    cancel = sub.add_parser("cancel", help="Cancel an open order")
    cancel.add_argument("--symbol", required=True)
    cancel.add_argument("--order-id", dest="order_id", required=True, type=int)
    cancel.set_defaults(func=cmd_cancel)

    account = sub.add_parser("account", help="Show account balance")
    account.set_defaults(func=cmd_account)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    setup_logging(args.log_level)
    args.func(args)


if __name__ == "__main__":
    main()
