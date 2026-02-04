# app/services/sources/infomoney.py
"""InfoMoney RSS news source."""
from typing import ClassVar

from app.services.sources.base import SourceRegistry
from app.services.sources.rss_source import RSSNewsSource


class InfoMoneySource(RSSNewsSource):
    """
    InfoMoney news source via RSS feeds.

    Covers: Mercados, Economia, Business sections.
    Relevant for financial/insurance news.
    """

    SOURCE_NAME: ClassVar[str] = "infomoney"
    FEED_URLS: ClassVar[list[str]] = [
        "https://www.infomoney.com.br/mercados/feed/",
        "https://www.infomoney.com.br/economia/feed/",
        "https://www.infomoney.com.br/business/feed/",
    ]


# Auto-register on import
SourceRegistry.register(InfoMoneySource())
