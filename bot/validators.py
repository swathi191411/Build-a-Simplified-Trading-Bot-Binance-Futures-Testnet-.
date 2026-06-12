"""
Input validation for trading bot CLI arguments.
All validation raises ValueError with a clear human-readable message.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional


VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}


def validate_symbol(symbol: str) -> str:
    """Ensure symbol is a non-empty uppercase string (e.g. BTCUSDT)."""
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValueError("Symbol cannot be empty.")
    if not symbol.isalnum():
        raise ValueError(f"Symbol '{symbol}' contains invalid characters. Expected alphanumeric (e.g. BTCUSDT).")
    return symbol


def validate_side(side: str) -> str:
    """Ensure side is BUY or SELL."""
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValueError(f"Side must be one of {sorted(VALID_SIDES)}. Got: '{side}'")
    return side


def validate_order_type(order_type: str) -> str:
    """Ensure order type is supported."""
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Order type must be one of {sorted(VALID_ORDER_TYPES)}. Got: '{order_type}'"
        )
    return order_type


def validate_quantity(quantity: str | float) -> Decimal:
    """Ensure quantity is a positive number."""
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Quantity '{quantity}' is not a valid number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be positive. Got: {qty}")
    return qty


def validate_price(price: Optional[str | float], order_type: str) -> Optional[Decimal]:
    """
    For LIMIT and STOP_MARKET orders, price is required and must be positive.
    For MARKET orders, price must be None.
    """
    if order_type == "MARKET":
        if price is not None:
            raise ValueError("Price must not be specified for MARKET orders.")
        return None

    if order_type in ("LIMIT", "STOP_MARKET"):
        if price is None:
            raise ValueError(f"Price is required for {order_type} orders.")
        try:
            p = Decimal(str(price))
        except InvalidOperation:
            raise ValueError(f"Price '{price}' is not a valid number.")
        if p <= 0:
            raise ValueError(f"Price must be positive. Got: {p}")
        return p

    return None


def validate_stop_price(
    stop_price: Optional[str | float], order_type: str
) -> Optional[Decimal]:
    """Stop price is required only for STOP_MARKET orders."""
    if order_type != "STOP_MARKET":
        return None
    if stop_price is None:
        raise ValueError("--stop-price is required for STOP_MARKET orders.")
    try:
        sp = Decimal(str(stop_price))
    except InvalidOperation:
        raise ValueError(f"Stop price '{stop_price}' is not a valid number.")
    if sp <= 0:
        raise ValueError(f"Stop price must be positive. Got: {sp}")
    return sp


def validate_all(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: Optional[str | float] = None,
    stop_price: Optional[str | float] = None,
) -> dict:
    """
    Run all validators and return a clean parameter dict.
    Raises ValueError on the first failed check.
    """
    return {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "order_type": validate_order_type(order_type),
        "quantity": validate_quantity(quantity),
        "price": validate_price(price, order_type.strip().upper()),
        "stop_price": validate_stop_price(stop_price, order_type.strip().upper()),
    }
