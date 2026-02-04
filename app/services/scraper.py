# app/services/scraper.py
"""
Apify-based web scraper service for Google News.

Uses the lhotanova/google-news-scraper actor to fetch news
about Brazilian insurers with proper rate limiting.

Note: This module now delegates to the sources module for the
actual implementation. It's kept for backward compatibility with
existing code that imports from here.
"""
import logging
from typing import Any

from app.services.sources import ScrapedNewsItem, GoogleNewsSource

logger = logging.getLogger(__name__)

# Re-export ScrapedNewsItem for backward compatibility
__all__ = ["ApifyScraperService", "ScrapedNewsItem"]


class ApifyScraperService:
    """
    Service for scraping Google News using Apify actors.

    Wraps the Apify client and provides methods for searching
    news about specific insurers using their name and ANS code.

    Note: This class now delegates to GoogleNewsSource internally
    while maintaining the same public interface for backward
    compatibility.
    """

    # Google News scraper actor from Apify Store
    GOOGLE_NEWS_ACTOR = "lhotanova/google-news-scraper"

    def __init__(self):
        """Initialize the service with GoogleNewsSource."""
        self._google_source = GoogleNewsSource()

    def search_google_news(
        self,
        query: str,
        language: str = "pt",
        country: str = "BR",
        max_results: int = 10,
        time_filter: str = "7d",
        timeout_secs: int = 300,
    ) -> list[ScrapedNewsItem]:
        """
        Search Google News for a query string.

        Args:
            query: Search query (supports quoted phrases and OR)
            language: Language code (pt for Portuguese)
            country: Country code (BR for Brazil)
            max_results: Maximum number of results to return
            time_filter: Time range (7d, 1m, 1y, etc.)
            timeout_secs: Actor execution timeout

        Returns:
            List of ScrapedNewsItem objects

        Note: language, country, time_filter, and timeout_secs are
        currently using default values in the underlying source.
        Future versions may support passing these through.
        """
        # Run the async method synchronously for backward compatibility
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If already in async context, use thread pool
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._google_source.search(query, max_results)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self._google_source.search(query, max_results)
                )
        except RuntimeError:
            # No event loop exists
            return asyncio.run(self._google_source.search(query, max_results))

    def search_insurer(
        self,
        insurer_name: str,
        ans_code: str,
        max_results: int = 10,
    ) -> list[ScrapedNewsItem]:
        """
        Search for news about a specific insurer.

        Combines insurer name and ANS code in search query
        for better accuracy and relevance.

        Args:
            insurer_name: Full insurer name
            ans_code: ANS registration code
            max_results: Maximum results to return

        Returns:
            List of ScrapedNewsItem objects
        """
        return self._google_source.search_insurer(
            insurer_name=insurer_name,
            ans_code=ans_code,
            max_results=max_results,
        )

    def health_check(self) -> dict[str, Any]:
        """
        Check Apify service connectivity.

        Returns dict with status and any error message.
        """
        # Run the async method synchronously
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._google_source.health_check()
                    )
                    return future.result()
            else:
                return loop.run_until_complete(
                    self._google_source.health_check()
                )
        except RuntimeError:
            return asyncio.run(self._google_source.health_check())
