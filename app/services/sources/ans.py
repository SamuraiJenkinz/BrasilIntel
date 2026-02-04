# app/services/sources/ans.py
"""ANS (Agencia Nacional de Saude Suplementar) official releases source."""
from typing import ClassVar

from app.services.sources.base import SourceRegistry
from app.services.sources.rss_source import RSSNewsSource


class ANSSource(RSSNewsSource):
    """
    ANS official news source via gov.br RSS.

    Official regulatory releases from Brazil's health
    insurance regulatory agency.
    """

    SOURCE_NAME: ClassVar[str] = "ans"
    FEED_URLS: ClassVar[list[str]] = [
        "https://www.gov.br/ans/pt-br/assuntos/noticias/RSS",
    ]


# Auto-register on import
SourceRegistry.register(ANSSource())
