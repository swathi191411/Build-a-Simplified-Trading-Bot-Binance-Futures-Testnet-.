"""
Binance Futures Testnet REST client.

Handles authentication (HMAC-SHA256 signatures), request building,
structured logging of every request/response, and error translation.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from decimal import Decimal
from typing import Any, Optional
from urllib.parse import urlencode

import requests

from bot.logging_config import get_logger

logger = get_logger("client")

BASE_URL = "https://testnet.binancefuture.com"
RECV_WINDOW = 5000  # ms


class BinanceAPIError(Exception):
    """Raised when the Binance API returns a non-2xx response or error payload."""

    def __init__(self, code: int, message: str, http_status: int = 0):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(f"[{code}] {message} (HTTP {http_status})")


class BinanceFuturesClient:
    """
    Thin wrapper around Binance USDT-M Futures REST API (Testnet).

    Args:
        api_key:    Testnet API key.
        api_secret: Testnet API secret.
        timeout:    HTTP request timeout in seconds.
    """

    def __init__(self, api_key: str, api_secret: str, timeout: int = 10):
        self._api_key = api_key
        self._api_secret = api_secret
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "X-MBX-APIKEY": self._api_key,
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }
        )
        logger.info("BinanceFuturesClient initialised (testnet=%s)", BASE_URL)

    # ── Internal helpers ───────────────────────────────────────────────────

    def _sign(self, params: dict) -> dict:
        """Append signature to a parameter dict (modifies in-place, returns it)."""
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = RECV_WINDOW
        query_string = urlencode(params)
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        signed: bool = False,
    ) -> Any:
        """
        Execute an HTTP request, log it, and return parsed JSON.

        Raises:
            BinanceAPIError: on API-level errors.
            requests.exceptions.RequestException: on network failures.
        """
        params = params or {}
        if signed:
            params = self._sign(params)

        url = f"{BASE_URL}{endpoint}"

        # Redact signature from logs
        log_params = {k: v for k, v in params.items() if k != "signature"}
        logger.debug("→ %s %s | params=%s", method.upper(), url, log_params)

        try:
            if method.upper() in ("GET", "DELETE"):
                response = self._session.request(
                    method, url, params=params, timeout=self._timeout
                )
            else:
                response = self._session.request(
                    method, url, data=params, timeout=self._timeout
                )
        except requests.exceptions.ConnectionError as exc:
            logger.error("Network connection error: %s", exc)
            raise
        except requests.exceptions.Timeout as exc:
            logger.error("Request timed out after %ds: %s", self._timeout, exc)
            raise

        logger.debug("← HTTP %s | body=%s", response.status_code, response.text[:500])

        try:
            data = response.json()
        except ValueError:
            logger.error("Non-JSON response: %s", response.text[:300])
            response.raise_for_status()
            return {}

        # Binance error envelope: {"code": -XXXX, "msg": "..."}
        if isinstance(data, dict) and "code" in data and data["code"] != 200:
            raise BinanceAPIError(
                code=data.get("code", 0),
                message=data.get("msg", "Unknown error"),
                http_status=response.status_code,
            )

        if not response.ok:
            raise BinanceAPIError(
                code=response.status_code,
                message=response.text,
                http_status=response.status_code,
            )

        return data

    # ── Public API ─────────────────────────────────────────────────────────

    def get_exchange_info(self) -> dict:
        """Fetch exchange info (symbol rules, filters, etc.)."""
        return self._request("GET", "/fapi/v1/exchangeInfo")

    def get_account(self) -> dict:
        """Fetch futures account details."""
        return self._request("GET", "/fapi/v2/account", signed=True)

    def get_position_risk(self, symbol: Optional[str] = None) -> list[dict]:
        """Fetch open position(s)."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v2/positionRisk", params=params, signed=True)

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Decimal,
        price: Optional[Decimal] = None,
        stop_price: Optional[Decimal] = None,
        time_in_force: str = "GTC",
    ) -> dict:
        """
        Place a new order on Binance Futures Testnet.

        Args:
            symbol:        Trading pair (e.g. 'BTCUSDT').
            side:          'BUY' or 'SELL'.
            order_type:    'MARKET', 'LIMIT', or 'STOP_MARKET'.
            quantity:      Order quantity.
            price:         Limit price (LIMIT orders only).
            stop_price:    Trigger price (STOP_MARKET orders only).
            time_in_force: 'GTC', 'IOC', or 'FOK' (LIMIT only).

        Returns:
            Raw API response dict.
        """
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": str(quantity),
        }

        if order_type == "LIMIT":
            if price is None:
                raise ValueError("price is required for LIMIT orders")
            params["price"] = str(price)
            params["timeInForce"] = time_in_force

        if order_type == "STOP_MARKET":
            if stop_price is None:
                raise ValueError("stop_price is required for STOP_MARKET orders")
            params["stopPrice"] = str(stop_price)

        logger.info(
            "Placing %s %s order | symbol=%s qty=%s price=%s stopPrice=%s",
            side,
            order_type,
            symbol,
            quantity,
            price,
            stop_price,
        )

        response = self._request("POST", "/fapi/v1/order", params=params, signed=True)
        logger.info(
            "Order placed | orderId=%s status=%s executedQty=%s avgPrice=%s",
            response.get("orderId"),
            response.get("status"),
            response.get("executedQty"),
            response.get("avgPrice"),
        )
        return response

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """Cancel an existing open order."""
        params = {"symbol": symbol, "orderId": order_id}
        logger.info("Cancelling order %s for %s", order_id, symbol)
        return self._request("DELETE", "/fapi/v1/order", params=params, signed=True)

    def get_open_orders(self, symbol: Optional[str] = None) -> list[dict]:
        """Return all open orders, optionally filtered by symbol."""
        params = {}
        if symbol:
            params["symbol"] = symbol
        return self._request("GET", "/fapi/v1/openOrders", params=params, signed=True)
