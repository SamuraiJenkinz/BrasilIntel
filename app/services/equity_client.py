"""
EquityPriceClient — MMC Core API equity price client for BrasilIntel.

Fetches current equity price data for a given ticker/exchange from the MMC Core
API equity endpoint. Used by the Phase 12 pipeline enrichment step to attach
real-time price data to classified articles that mention tracked insurers.

API contract (per equity.yaml — Equity Price API v1.1.1):
    Quote:  GET {base_url}/equity-price/v1/quotes/{tickerSymbol}
    By exchange: GET {base_url}/equity-price/v1/exchanges/{exchange}/quotes/{tickerSymbol}
            Headers: X-Api-Key: {key}
            Returns: { content: { tickerSymbol, exchange, currency, price, change,
                       percent, priceDetails: {maximumPrice, minimumPrice, openingPrice,
                       closingPrice}, tradeTime, volume } }

Authentication:
    X-Api-Key header only — same as FactivaCollector, no JWT/Bearer needed.
    Credentials read from Settings (mmc_api_base_url, mmc_api_key).

Error handling:
    - Returns None on any failure (HTTP error, timeout, parse error)
    - Never raises exceptions to callers — caller pipeline continues without price data
    - All outcomes recorded as ApiEvent(type=EQUITY_FETCH) for dashboard visibility
    - On 4xx HTTP status: logs warning, returns None (same as FactivaCollector pattern)
"""
import json
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings
from app.database import SessionLocal
from app.models.api_event import ApiEvent, ApiEventType


class EquityPriceClient:
    """
    MMC Core API equity price client for BrasilIntel.

    Fetches current price data for a given ticker symbol and exchange code
    using the MMC Equity Price API. Returns a normalized price dict or None
    on any failure.

    Modeled exactly on FactivaCollector for consistency:
    - Same httpx + tenacity retry pattern
    - Same X-Api-Key header authentication
    - Same _record_event() isolation pattern
    - Same is_configured() guard pattern

    Usage:
        client = EquityPriceClient()
        if client.is_configured():
            price_data = client.get_price("BBSE3", "BVMF", run_id=run_id)
            if price_data:
                # price_data = {"ticker": "BBSE3", "exchange": "BVMF",
                #               "price": 45.50, "change": 1.25, "change_pct": 2.82,
                #               "currency": "BRL", "trade_time": "2026-02-20T15:30:00Z",
                #               "volume": 1234567}

    Response structure (per equity.yaml):
        { content: { tickerSymbol, exchange, currency, price, change, percent,
                     priceDetails: {maximumPrice, minimumPrice, openingPrice, closingPrice},
                     tradeTime, volume } }
    """

    # Per equity.yaml: /equity-price/v1/quotes/{tickerSymbol}
    BASE_QUOTE_PATH = "/equity-price/v1/quotes"
    # Per equity.yaml: /equity-price/v1/exchanges/{exchange}/quotes/{tickerSymbol}
    BASE_EXCHANGE_QUOTE_PATH = "/equity-price/v1/exchanges"

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url: str = settings.mmc_api_base_url.rstrip("/")
        self.api_key: str = settings.mmc_api_key
        self.logger = structlog.get_logger(__name__).bind(service="equity_price_client")

    def is_configured(self) -> bool:
        """Return True if base_url and api_key are both present in Settings."""
        return bool(self.base_url and self.api_key)

    def get_price(
        self,
        ticker: str,
        exchange: str = "BVMF",
        run_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch current equity price data for a ticker/exchange pair.

        Returns a normalized price dict on success, or None on any failure.
        Never raises exceptions — callers can always safely ignore the return value.

        Args:
            ticker:   Exchange ticker symbol (e.g. "BBSE3", "PSSA3")
            exchange: Exchange code (e.g. "BVMF", "NYSE") — default "BVMF"
            run_id:   Optional pipeline run ID for event attribution

        Returns:
            Dict with keys: ticker, exchange, price, change, change_pct
            All price fields may be None if the API response omits them.
            Returns None on any failure (HTTP error, timeout, parse error).
        """
        try:
            response_data = self._fetch_price(ticker=ticker, exchange=exchange)

            if response_data is None:
                # 4xx response — already logged in _fetch_price
                self._record_event(
                    event_type=ApiEventType.EQUITY_FETCH,
                    success=False,
                    detail=json.dumps({
                        "ticker": ticker,
                        "exchange": exchange,
                        "error": "4xx_client_error",
                    }),
                    run_id=run_id,
                )
                return None

            # Per equity.yaml: response is { content: { tickerSymbol, exchange, ... } }
            content = response_data.get("content", response_data)

            price = content.get("price")
            change = content.get("change")
            change_pct = content.get("percent")
            currency = content.get("currency")
            trade_time = content.get("tradeTime")
            volume = content.get("volume")

            self.logger.info(
                "equity_price_fetched",
                ticker=ticker,
                exchange=exchange,
                price=price,
            )

            self._record_event(
                event_type=ApiEventType.EQUITY_FETCH,
                success=True,
                detail=json.dumps({"ticker": ticker, "price": price}),
                run_id=run_id,
            )

            return {
                "ticker": ticker,
                "exchange": content.get("exchange", exchange),
                "price": price,
                "change": change,
                "change_pct": change_pct,
                "currency": currency,
                "trade_time": trade_time,
                "volume": volume,
            }

        except Exception as exc:
            self.logger.warning(
                "equity_price_fetch_failed",
                ticker=ticker,
                exchange=exchange,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            self._record_event(
                event_type=ApiEventType.EQUITY_FETCH,
                success=False,
                detail=json.dumps({
                    "ticker": ticker,
                    "exchange": exchange,
                    "error": type(exc).__name__,
                    "message": str(exc)[:200],
                }),
                run_id=run_id,
            )
            return None

    def _build_headers(self) -> Dict[str, str]:
        """
        Build request headers for equity API calls.

        Uses X-Api-Key authentication only — no JWT/Bearer token required.
        Identical to FactivaCollector._build_headers().
        """
        return {
            "X-Api-Key": self.api_key,
            "Accept": "application/json",
        }

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    )
    def _fetch_price(
        self,
        ticker: str,
        exchange: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Execute equity price API call with tenacity retry.

        Per equity.yaml:
        - Any exchange: GET /equity-price/v1/quotes/{tickerSymbol}
        - Specific exchange: GET /equity-price/v1/exchanges/{exchange}/quotes/{tickerSymbol}

        Returns None on 4xx client errors so the caller can record a failed event
        and return None to its caller — same pattern as FactivaCollector._fetch_article.

        Args:
            ticker:   Exchange ticker symbol
            exchange: Exchange code

        Returns:
            Parsed JSON response dict on success.
            None on 4xx client errors (ticker not found, not authorized).

        Raises:
            httpx.TimeoutException: On timeout (triggers tenacity retry).
            httpx.ConnectError: On connection failure (triggers tenacity retry).
            httpx.HTTPStatusError: On 5xx server errors after raise_for_status.
        """
        # Use exchange-specific endpoint when exchange is provided
        if exchange:
            url = f"{self.base_url}{self.BASE_EXCHANGE_QUOTE_PATH}/{exchange}/quotes/{ticker}"
        else:
            url = f"{self.base_url}{self.BASE_QUOTE_PATH}/{ticker}"

        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, headers=self._build_headers())

            # 4xx = ticker not found, unauthorized, bad request
            # Log warning and return None so caller uses graceful fallback
            if 400 <= response.status_code < 500:
                self.logger.warning(
                    "equity_price_client_error",
                    ticker=ticker,
                    exchange=exchange,
                    status_code=response.status_code,
                )
                return None

            response.raise_for_status()
            return response.json()

    def _record_event(
        self,
        event_type: ApiEventType,
        success: bool,
        detail: Optional[str] = None,
        run_id: Optional[int] = None,
    ) -> None:
        """
        Record an equity API event to the api_events table.

        Opens its own isolated DB session so event recording never interferes
        with caller's transaction context. Failures are swallowed — event recording
        must never crash the price fetch flow.

        Identical pattern to FactivaCollector._record_event().

        Args:
            event_type: ApiEventType.EQUITY_FETCH or ApiEventType.EQUITY_FALLBACK
            success:    True if the operation succeeded
            detail:     JSON-safe string with event context (no secrets, max 500 chars)
            run_id:     Optional pipeline run ID (None for out-of-pipeline calls)
        """
        try:
            with SessionLocal() as session:
                event = ApiEvent(
                    event_type=event_type,
                    api_name="equity",
                    timestamp=datetime.utcnow(),
                    success=success,
                    detail=detail[:500] if detail else None,
                    run_id=run_id,
                )
                session.add(event)
                session.commit()
        except Exception as exc:
            # Never propagate DB errors into the price fetch flow
            self.logger.warning(
                "equity_api_event_record_failed",
                event_type=event_type.value,
                error=str(exc),
            )
