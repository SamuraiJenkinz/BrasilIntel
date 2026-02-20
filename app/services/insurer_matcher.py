"""
Deterministic insurer matching service for BrasilIntel.

Matches news articles to insurers using fast string matching against
insurer names and search_terms. Handles ~80% of assignments without AI,
avoiding costs for clear cases.
"""
import re
import unicodedata
from typing import Any

import structlog

from app.models.insurer import Insurer
from app.schemas.matching import MatchResult


logger = structlog.get_logger(__name__)


class InsurerMatcher:
    """
    Service for matching news articles to insurers.

    Uses deterministic name/search_term matching as first pass,
    with AI disambiguation for ambiguous cases (Plan 02).
    """

    def __init__(self):
        """Initialize matcher with structlog logger."""
        self.logger = structlog.get_logger(__name__)

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for accent-insensitive matching.

        Handles Portuguese accented characters (SulAmérica vs SulAmerica)
        and case variations.

        Args:
            text: Text to normalize

        Returns:
            Normalized lowercase text without accents
        """
        if not text:
            return ""

        # Decompose accents using NFKD (compatibility decomposition)
        normalized = unicodedata.normalize('NFKD', text)

        # Filter out combining characters (accents)
        without_accents = ''.join(
            char for char in normalized
            if not unicodedata.combining(char)
        )

        # Lowercase and strip whitespace
        return without_accents.lower().strip()

    def _deterministic_match(
        self,
        article: dict[str, Any],
        insurers: list[Insurer]
    ) -> list[int]:
        """
        Perform deterministic matching using name and search_terms.

        Uses word-boundary regex to avoid false positives (e.g., "Sul" in "consulta").
        Skips short names (<4 chars) that need AI disambiguation.

        Args:
            article: Article dict with 'title' and 'description' keys
            insurers: List of Insurer ORM objects

        Returns:
            List of matched insurer IDs
        """
        # Combine title and description into single searchable content
        title = article.get('title', '')
        description = article.get('description', '')
        content = self._normalize_text(f"{title} {description}")

        if not content:
            return []

        matched_ids = []

        for insurer in insurers:
            # Check insurer name
            name_normalized = self._normalize_text(insurer.name)

            # Skip short names (high false positive risk - route to AI)
            if len(name_normalized) < 4:
                self.logger.debug(
                    "Skipping short name for deterministic match",
                    insurer_id=insurer.id,
                    name=insurer.name,
                    name_length=len(name_normalized)
                )
                continue

            # Word-boundary matching to avoid substring false positives
            name_pattern = rf'\b{re.escape(name_normalized)}\b'
            if re.search(name_pattern, content):
                matched_ids.append(insurer.id)
                self.logger.debug(
                    "Name match found",
                    insurer_id=insurer.id,
                    name=insurer.name,
                    article_title=title
                )
                continue  # Move to next insurer

            # Check search_terms if present
            if insurer.search_terms:
                search_terms = [
                    term.strip()
                    for term in insurer.search_terms.split(',')
                    if term.strip()
                ]

                for term in search_terms:
                    term_normalized = self._normalize_text(term)

                    # Skip short search terms too
                    if len(term_normalized) < 4:
                        continue

                    term_pattern = rf'\b{re.escape(term_normalized)}\b'
                    if re.search(term_pattern, content):
                        matched_ids.append(insurer.id)
                        self.logger.debug(
                            "Search term match found",
                            insurer_id=insurer.id,
                            term=term,
                            article_title=title
                        )
                        break  # Found a match, move to next insurer

        return matched_ids

    def match_article(
        self,
        article: dict[str, Any],
        insurers: list[Insurer]
    ) -> MatchResult:
        """
        Match a single article to insurers.

        Returns MatchResult with appropriate method and confidence based on
        number of deterministic matches found.

        Args:
            article: Article dict with 'title' and 'description' keys
            insurers: List of Insurer ORM objects to match against

        Returns:
            MatchResult indicating matched insurers, confidence, and method
        """
        matched_ids = self._deterministic_match(article, insurers)
        match_count = len(matched_ids)

        if match_count == 1:
            # Single clear match - high confidence
            insurer = next(i for i in insurers if i.id == matched_ids[0])
            return MatchResult(
                insurer_ids=matched_ids,
                confidence=0.95,
                method="deterministic_single",
                reasoning=f"Exact name match: {insurer.name}"
            )

        elif 2 <= match_count <= 3:
            # Multiple matches (likely multi-insurer article)
            return MatchResult(
                insurer_ids=matched_ids,
                confidence=0.85,
                method="deterministic_multi",
                reasoning=f"Found {match_count} name matches"
            )

        elif match_count > 3:
            # Too many matches - needs AI disambiguation
            return MatchResult(
                insurer_ids=[],
                confidence=0.0,
                method="unmatched",
                reasoning=f"Too many matches ({match_count}), needs AI disambiguation"
            )

        else:
            # No matches - AI will attempt in Plan 02
            return MatchResult(
                insurer_ids=[],
                confidence=0.0,
                method="unmatched",
                reasoning="No clear deterministic match"
            )

    def match_batch(
        self,
        articles: list[dict[str, Any]],
        insurers: list[Insurer]
    ) -> list[MatchResult]:
        """
        Match a batch of articles to insurers.

        Logs batch statistics including match method distribution.

        Args:
            articles: List of article dicts with 'title' and 'description'
            insurers: List of Insurer ORM objects to match against

        Returns:
            List of MatchResult objects, one per article
        """
        self.logger.info(
            "Starting batch matching",
            article_count=len(articles),
            insurer_count=len(insurers)
        )

        results = []
        stats = {
            "deterministic_single": 0,
            "deterministic_multi": 0,
            "unmatched": 0,
        }

        for article in articles:
            result = self.match_article(article, insurers)
            results.append(result)
            stats[result.method] += 1

        self.logger.info(
            "Batch matching complete",
            total_articles=len(articles),
            deterministic_single=stats["deterministic_single"],
            deterministic_multi=stats["deterministic_multi"],
            unmatched=stats["unmatched"]
        )

        return results
