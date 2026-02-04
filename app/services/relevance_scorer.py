"""
AI relevance scoring service for pre-filtering news items.

Uses a two-pass approach to minimize Azure OpenAI costs:
1. Keyword filtering (free) - fast string matching
2. AI scoring (paid) - only for marginal cases above threshold

All prompts in Portuguese for Brazilian insurance context.
"""
import logging
from typing import Any

from openai import AzureOpenAI

from app.config import get_settings
from app.services.sources import ScrapedNewsItem

logger = logging.getLogger(__name__)


# Portuguese prompt for relevance scoring
RELEVANCE_SYSTEM_PROMPT = """Você é um analista especializado em seguros no Brasil.
Sua tarefa é avaliar se notícias são relevantes para monitoramento de seguradoras.

Critérios de relevância ALTA:
- Menciona diretamente a seguradora ou seus produtos
- Trata de fusões, aquisições ou mudanças de liderança
- Discute ações regulatórias da ANS ou Susep
- Reporta resultados financeiros ou mudanças de rating
- Menciona processos judiciais ou investigações

Critérios de relevância BAIXA:
- Menção genérica ao setor sem relação direta
- Notícias sobre seguros em geral sem citar a empresa
- Conteúdo duplicado ou irrelevante
- Publicidade ou conteúdo promocional

Para cada notícia, responda com "relevant" ou "not_relevant"."""


class RelevanceScorer:
    """
    Service for scoring news item relevance before expensive classification.

    Uses a two-pass filtering approach:
    1. Keyword filtering (free): Fast string matching on insurer name
    2. AI filtering (paid): Azure OpenAI scoring for marginal cases

    The keyword filter runs first to eliminate obvious non-matches.
    AI scoring is only used when item count exceeds the threshold.
    """

    def __init__(self):
        settings = get_settings()

        if not settings.is_azure_openai_configured():
            logger.warning("Azure OpenAI not configured - AI scoring disabled")
            self.client = None
            self.model = None
        else:
            self.client = AzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
            )
            self.model = settings.azure_openai_deployment

        self.use_ai = settings.use_ai_relevance_scoring
        self.keyword_threshold = settings.relevance_keyword_threshold
        self.ai_batch_size = settings.relevance_ai_batch_size

    def score_batch(
        self,
        items: list[ScrapedNewsItem],
        insurer_name: str,
        max_results: int | None = None,
    ) -> list[ScrapedNewsItem]:
        """
        Score and filter a batch of news items for relevance.

        Two-pass filtering:
        1. Keyword filter (free) - keeps items mentioning insurer name
        2. AI filter (paid) - scores remaining items if above threshold

        Args:
            items: List of ScrapedNewsItem to filter
            insurer_name: Insurer name for relevance matching
            max_results: Optional limit on returned items

        Returns:
            Filtered list of relevant ScrapedNewsItem objects
        """
        if not items:
            return []

        logger.info(f"Scoring {len(items)} items for '{insurer_name}'")

        # Pass 1: Keyword filtering (free)
        keyword_matches = self._keyword_filter(items, insurer_name)
        logger.debug(f"Keyword filter: {len(keyword_matches)}/{len(items)} matches")

        # Pass 2: AI filtering (paid) - only if enabled and above threshold
        if (
            self.use_ai
            and self.client
            and len(keyword_matches) > self.keyword_threshold
        ):
            logger.info(
                f"Items ({len(keyword_matches)}) exceed threshold "
                f"({self.keyword_threshold}), applying AI filter"
            )
            filtered = self._ai_filter(keyword_matches, insurer_name)
        else:
            filtered = keyword_matches

        # Apply max_results limit
        if max_results and len(filtered) > max_results:
            filtered = filtered[:max_results]

        logger.info(
            f"Relevance scoring complete: {len(items)} -> {len(filtered)} items"
        )
        return filtered

    def _keyword_filter(
        self,
        items: list[ScrapedNewsItem],
        insurer_name: str,
    ) -> list[ScrapedNewsItem]:
        """
        Fast keyword-based filtering on insurer name.

        Checks if any part of the insurer name appears in the title
        or description. Case insensitive matching.

        Args:
            items: List of items to filter
            insurer_name: Insurer name to match

        Returns:
            Items matching any name part
        """
        # Split name into searchable parts (e.g., "Amil Saude" -> ["amil", "saude"])
        name_parts = [
            part.lower()
            for part in insurer_name.split()
            if len(part) > 2  # Skip short words like "de", "da"
        ]

        if not name_parts:
            # No valid parts to match - return all items
            return items

        matches = []
        for item in items:
            # Combine title and description for matching
            text = (item.title or "").lower()
            if item.description:
                text += " " + item.description.lower()

            # Check if any name part appears in text
            if any(part in text for part in name_parts):
                matches.append(item)

        return matches

    def _ai_filter(
        self,
        items: list[ScrapedNewsItem],
        insurer_name: str,
    ) -> list[ScrapedNewsItem]:
        """
        AI-based relevance filtering using Azure OpenAI.

        Processes items in batches and scores each for relevance.
        Uses fail-open error handling (keeps items on error).

        Args:
            items: List of items to score
            insurer_name: Insurer name for context

        Returns:
            Items scored as relevant
        """
        relevant_items = []

        # Process in batches
        for i in range(0, len(items), self.ai_batch_size):
            batch = items[i : i + self.ai_batch_size]

            try:
                batch_results = self._score_batch_with_ai(batch, insurer_name)

                # Keep items scored as relevant
                for item, is_relevant in zip(batch, batch_results):
                    if is_relevant:
                        relevant_items.append(item)

            except Exception as e:
                # Fail-open: keep all items in batch on error
                logger.error(f"AI scoring failed, keeping batch: {e}")
                relevant_items.extend(batch)

        return relevant_items

    def _score_batch_with_ai(
        self,
        items: list[ScrapedNewsItem],
        insurer_name: str,
    ) -> list[bool]:
        """
        Score a batch of items using Azure OpenAI.

        Args:
            items: Batch of items to score
            insurer_name: Insurer name for context

        Returns:
            List of booleans (True = relevant)
        """
        if not self.client:
            # No client - keep all items
            return [True] * len(items)

        # Build prompt with numbered items
        items_text = "\n".join([
            f"{idx + 1}. {item.title}"
            + (f" - {item.description[:200]}" if item.description else "")
            for idx, item in enumerate(items)
        ])

        user_prompt = f"""Avalie a relevância destas notícias para a seguradora "{insurer_name}".

Notícias:
{items_text}

Para cada notícia (1 a {len(items)}), responda em uma linha:
[numero]: [relevant/not_relevant]

Exemplo:
1: relevant
2: not_relevant
3: relevant"""

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": RELEVANCE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,  # Deterministic outputs
                max_tokens=200,  # Short responses only
            )

            response_text = completion.choices[0].message.content or ""
            return self._parse_relevance_response(response_text, len(items))

        except Exception as e:
            logger.error(f"AI scoring API call failed: {e}")
            # Fail-open: return all as relevant
            return [True] * len(items)

    def _parse_relevance_response(
        self,
        response: str,
        expected_count: int,
    ) -> list[bool]:
        """
        Parse AI response to extract relevance decisions.

        Expects format like:
        1: relevant
        2: not_relevant

        Args:
            response: Raw response text
            expected_count: Number of items expected

        Returns:
            List of booleans (True = relevant)
        """
        results = [True] * expected_count  # Default: keep all (fail-open)

        for line in response.strip().split("\n"):
            line = line.strip().lower()
            if ":" not in line:
                continue

            try:
                num_part, decision = line.split(":", 1)
                # Extract number (handle "1." or "1" or "#1")
                num_str = "".join(c for c in num_part if c.isdigit())
                if not num_str:
                    continue

                idx = int(num_str) - 1  # Convert to 0-based index
                if 0 <= idx < expected_count:
                    # Check for not_relevant first (more specific)
                    if "not_relevant" in decision or "not relevant" in decision:
                        results[idx] = False
                    elif "relevant" in decision:
                        results[idx] = True
                    # Otherwise keep default (True - fail-open)

            except (ValueError, IndexError):
                continue

        return results

    def health_check(self) -> dict[str, Any]:
        """
        Check service status and configuration.

        Returns:
            Dict with status and configuration details
        """
        if not self.client:
            return {
                "status": "degraded",
                "message": "Azure OpenAI not configured - keyword filtering only",
                "ai_enabled": False,
            }

        if not self.use_ai:
            return {
                "status": "ok",
                "message": "AI scoring disabled by configuration",
                "ai_enabled": False,
            }

        try:
            # Quick test call
            self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return {
                "status": "ok",
                "ai_enabled": True,
                "keyword_threshold": self.keyword_threshold,
                "batch_size": self.ai_batch_size,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "ai_enabled": False,
            }
