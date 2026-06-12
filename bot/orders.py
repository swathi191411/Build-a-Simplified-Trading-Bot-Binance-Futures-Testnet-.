"""
Order placement logic layer.

This module sits between the CLI and the raw API client.
It validates inputs, calls the client, formats results,
and provides a clean OrderResult dataclass.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional

from bot.client import BinanceFuturesClient, BinanceAPIError
from bot.logging_config import get_logger
from bot.validators import validate_all

logger = get_logger("orders")


@dataclass
class OrderResult:
    """Structured representation of a placed order."""

    success: bool
    order_id: Optional[int] = None
    client_order_id: Optional[str] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    order_type: Optional[str] = None
    status: Optional[str] = None
    quantity: Optional[str] = None
    executed_qty: Optional[str] = None
    avg_price: Optional[str] = None
    price: Optional[str] = None
    raw: dict = field(default_factory=dict)
    error: Optional[str] = None

    def summary(self) -> str:
        """Return a human-readable summary string."""
        if not self.success:
            return f"✗  Order FAILED: {self.error}"

        lines = [
            "✓  Order placed successfully",
            f"   Order ID      : {self.order_id}",
            f"   Symbol        : {self.symbol}",
            f"   Side          : {self.side}",
            f"   Type          : {self.order_type}",
            f"   Status        : {self.status}",
            f"   Quantity      : {self.quantity}",
            f"   Executed Qty  : {self.executed_qty}",
        ]
        if self.avg_price and float(self.avg_price) > 0:
            lines.append(f"   Avg Price     : {self.avg_price}")
        if self.price and float(self.price) > 0:
            lines.append(f"   Limit Price   : {self.price}")
        return "\n".join(lines)


def _parse_response(raw: dict) -> OrderResult:
    """Map a raw Binance order response to OrderResult."""
    return OrderResult(
        success=True,
        order_id=raw.get("orderId"),
        client_order_id=raw.get("clientOrderId"),
        symbol=raw.get("symbol"),
        side=raw.get("side"),
        order_type=raw.get("type"),
        status=raw.get("status"),
        quantity=raw.get("origQty"),
        executed_qty=raw.get("executedQty"),
        avg_price=raw.get("avgPrice"),
        price=raw.get("price"),
        raw=raw,
    )


def place_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: Optional[str | float] = None,
    stop_price: Optional[str | float] = None,
    time_in_force: str = "GTC",
) -> OrderResult:
    """
    Validate inputs and place an order via the Binance client.

    Args:
        client:         Initialised BinanceFuturesClient.
        symbol:         Trading pair.
        side:           BUY or SELL.
        order_type:     MARKET, LIMIT, or STOP_MARKET.
        quantity:       Order quantity.
        price:          Limit price (LIMIT only).
        stop_price:     Trigger price (STOP_MARKET only).
        time_in_force:  GTC / IOC / FOK (LIMIT only).

    Returns:
        OrderResult (success=True) or OrderResult (success=False, error=...).
    """
    # ── Validation ─────────────────────────────────────────────────────────
    try:
        params = validate_all(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
        )
    except ValueError as exc:
        logger.warning("Validation failed: %s", exc)
        return OrderResult(success=False, error=str(exc))

    logger.info(
        "Order request | symbol=%s side=%s type=%s qty=%s price=%s stopPrice=%s",
        params["symbol"],
        params["side"],
        params["order_type"],
        params["quantity"],
        params["price"],
        params["stop_price"],
    )

    # ── API call ───────────────────────────────────────────────────────────
    try:
        raw = client.place_order(
            symbol=params["symbol"],
            side=params["side"],
            order_type=params["order_type"],
            quantity=params["quantity"],
            price=params["price"],
            stop_price=params["stop_price"],
            time_in_force=time_in_force,
        )
    except BinanceAPIError as exc:
        logger.error("API error placing order: %s", exc)
        return OrderResult(success=False, error=str(exc))
    except Exception as exc:
        logger.exception("Unexpected error placing order: %s", exc)
        return OrderResult(success=False, error=f"Unexpected error: {exc}")

    result = _parse_response(raw)
    logger.info("Order result | %s", json.dumps(raw))
    return result
