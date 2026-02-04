# app/services/sources/estadao.py
"""
Brazilian financial news RSS source.

Note: Original Estadao RSS feeds were deprecated. Using G1 Economia (Globo)
as alternative Brazilian financial news source with working RSS feeds.
"""
from typing import ClassVar

from app.services.sources.base import SourceRegistry
from app.services.sources.rss_source import RSSNewsSource


class EstadaoSource(RSSNewsSource):
    """
    Brazilian financial news source via RSS feeds.

    Uses G1 Economia (Globo) RSS feeds as Estadao deprecated their
    RSS service. Covers economia section for insurance/financial news.

    Note: SOURCE_NAME kept as 'estadao' for backward compatibility.
    """

    SOURCE_NAME: ClassVar[str] = "estadao"
    FEED_URLS: ClassVar[list[str]] = [
        "https://g1.globo.com/rss/g1/economia/",
    ]


# Auto-register on import
SourceRegistry.register(EstadaoSource())
