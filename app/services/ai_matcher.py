"""
AI-assisted insurer matching service for ambiguous articles.

When deterministic matching cannot resolve an article to specific insurers
(0 matches or too many matches), this service uses Azure OpenAI structured
output to identify which of the 897 tracked insurers are mentioned.

Follows the exact Azure OpenAI client initialization pattern from classifier.py,
including corporate proxy URL detection logic critical for BrasilIntel.
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from openai import AzureOpenAI, OpenAI
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings
from app.database import SessionLocal
from app.models.api_event import ApiEvent, ApiEventType
from app.models.insurer import Insurer
from app.schemas.matching import MatchResult


class InsurerMatchResponse(BaseModel):
    """Structured output from Azure OpenAI for insurer matching."""
    insurer_ids: list[int] = Field(
        description="IDs of insurers mentioned in the article from the provided list. Empty if none.",
        default_factory=list
    )
    confidence: float = Field(
        description="Confidence 0-1 that the identification is correct",
        ge=0.0, le=1.0
    )
    reasoning: str = Field(
        description="Brief explanation of which insurer(s) were identified and why"
    )


# System prompt in Portuguese for consistency with classifier
SYSTEM_PROMPT = """Você é um assistente de IA que identifica quais seguradoras brasileiras são mencionadas em artigos de notícias.

Lista de seguradoras disponíveis:
{insurer_context}

Analise o artigo e identifique qual(is) seguradora(s) da lista acima são mencionadas.
- Retorne os IDs da lista acima.
- Se nenhuma seguradora for claramente mencionada, retorne uma lista vazia.
- Se múltiplas seguradoras forem mencionadas, retorne todos os IDs relevantes.
- Considere variações de nomes (com e sem acentos, abreviações, nomes comerciais)."""


class AIInsurerMatcher:
    """
    AI-assisted insurer matching service using Azure OpenAI.

    Uses structured outputs with Pydantic models to ensure consistent
    identification of insurers mentioned in news articles.

    Handles ambiguous cases where deterministic matching fails:
    - 0 matches: no clear name/term match found
    - >3 matches: too many possibilities (e.g., generic term "seguro")

    Gracefully degrades when Azure OpenAI is not configured or fails.
    """

    # Maximum insurers to send in context to stay within token limits
    MAX_INSURER_CONTEXT = 200

    def __init__(self):
        settings = get_settings()
        self.logger = structlog.get_logger(__name__).bind(service="ai_matcher")
        self.settings = settings

        if not settings.is_azure_openai_configured():
            self.logger.warning("Azure OpenAI not configured - AI matching will fail gracefully")
            self.client = None
            self.model = None
        else:
            endpoint = settings.azure_openai_endpoint
            api_key = settings.get_azure_openai_key()

            # Detect corporate proxy URL format (contains full path to chat/completions)
            if "/deployments/" in endpoint and "/chat/completions" in endpoint:
                # Extract base URL up to deployment (includes /deployments/{model})
                # Format: .../v1/deployments/{deployment}/chat/completions
                # OpenAI client will append /chat/completions to base_url
                import re
                match = re.search(r"(.+/deployments/[^/]+)/chat/completions", endpoint)
                if match:
                    base_url = match.group(1)
                    # Extract model name for logging
                    model_match = re.search(r"/deployments/([^/]+)", endpoint)
                    self.model = model_match.group(1) if model_match else "unknown"
                    self.logger.info(f"Using proxy endpoint: {base_url}, model: {self.model}")
                    self.client = OpenAI(
                        base_url=base_url,
                        api_key=api_key,
                    )
                else:
                    self.logger.error(f"Could not parse proxy endpoint: {endpoint}")
                    self.client = None
                    self.model = None
            else:
                # Standard Azure OpenAI endpoint
                self.client = AzureOpenAI(
                    azure_endpoint=endpoint,
                    api_key=api_key,
                    api_version=settings.azure_openai_api_version,
                )
                self.model = settings.azure_openai_deployment

    def is_configured(self) -> bool:
        """Return True if Azure OpenAI client is available."""
        return self.client is not None

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
    )
    def ai_match(
        self,
        article: Dict[str, Any],
        insurers: List[Insurer],
        run_id: Optional[int] = None,
    ) -> MatchResult:
        """
        Use Azure OpenAI to identify which insurers are mentioned in an article.

        This is called when deterministic matching fails (0 matches or >3 matches).
        The AI receives a list of insurer names/IDs and returns structured output
        identifying which insurers are mentioned.

        Args:
            article: Dict with 'title' and 'description' keys
            insurers: List of Insurer ORM objects to consider
            run_id: Optional pipeline run ID for event attribution

        Returns:
            MatchResult with method="ai_disambiguation" or method="unmatched"
            if AI is unavailable or fails
        """
        if self.client is None:
            self.logger.warning("ai_match_unavailable", reason="Azure OpenAI not configured")
            return MatchResult(
                insurer_ids=[],
                confidence=0.0,
                method="unmatched",
                reasoning="AI matching unavailable — Azure OpenAI not configured"
            )

        # Build insurer context string
        # Sort by enabled=True first, then alphabetically
        # Limit to MAX_INSURER_CONTEXT to stay within token limits
        sorted_insurers = sorted(
            insurers,
            key=lambda ins: (not ins.enabled, ins.name.lower())
        )

        if len(sorted_insurers) > self.MAX_INSURER_CONTEXT:
            self.logger.warning(
                "ai_match_insurer_truncation",
                total_insurers=len(sorted_insurers),
                max_context=self.MAX_INSURER_CONTEXT,
                message=f"Truncating to first {self.MAX_INSURER_CONTEXT} insurers"
            )
            sorted_insurers = sorted_insurers[:self.MAX_INSURER_CONTEXT]

        insurer_context_lines = []
        for ins in sorted_insurers:
            search_terms_display = ins.search_terms or "nenhum"
            insurer_context_lines.append(
                f"ID {ins.id}: {ins.name} (termos: {search_terms_display})"
            )

        insurer_context = "\n".join(insurer_context_lines)

        # Build user prompt: article title + first 500 chars of description
        article_title = article.get("title", "")[:200]
        article_description = article.get("description", "")[:500]
        user_prompt = f"""Título: {article_title}

Descrição: {article_description}

Qual(is) seguradora(s) são mencionadas neste artigo?"""

        try:
            self.logger.info(
                "ai_match_started",
                article_title=article_title[:100],
                insurer_count=len(sorted_insurers),
            )

            completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT.format(insurer_context=insurer_context)},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=InsurerMatchResponse,
                temperature=0,  # Deterministic outputs
            )

            parsed_result = completion.choices[0].message.parsed

            # Validate insurer_ids — filter out any IDs not in the provided list
            # (AI hallucination guard)
            valid_insurer_ids = {ins.id for ins in sorted_insurers}
            validated_ids = [
                ins_id for ins_id in parsed_result.insurer_ids
                if ins_id in valid_insurer_ids
            ]

            if len(validated_ids) != len(parsed_result.insurer_ids):
                self.logger.warning(
                    "ai_match_hallucination_detected",
                    original_ids=parsed_result.insurer_ids,
                    validated_ids=validated_ids,
                    message="AI returned IDs not in provided list"
                )

            self.logger.info(
                "ai_match_completed",
                matched_ids=validated_ids,
                confidence=parsed_result.confidence,
                reasoning=parsed_result.reasoning[:200],
            )

            # Record successful ApiEvent
            self._record_event(
                event_type=ApiEventType.NEWS_FETCH,  # Reuse existing type
                success=True,
                detail=json.dumps({
                    "article_title": article_title[:100],
                    "matched_ids": validated_ids,
                    "confidence": parsed_result.confidence,
                }),
                run_id=run_id,
            )

            return MatchResult(
                insurer_ids=validated_ids,
                confidence=parsed_result.confidence,
                method="ai_disambiguation",
                reasoning=parsed_result.reasoning
            )

        except Exception as exc:
            self.logger.warning(
                "ai_match_failed",
                error_type=type(exc).__name__,
                error=str(exc),
                article_title=article_title[:100],
            )

            # Record failed ApiEvent
            self._record_event(
                event_type=ApiEventType.NEWS_FETCH,  # Reuse existing type
                success=False,
                detail=json.dumps({
                    "article_title": article_title[:100],
                    "error": type(exc).__name__,
                    "message": str(exc)[:200],
                }),
                run_id=run_id,
            )

            return MatchResult(
                insurer_ids=[],
                confidence=0.0,
                method="unmatched",
                reasoning=f"AI match failed: {type(exc).__name__}"
            )

    def _record_event(
        self,
        event_type: ApiEventType,
        success: bool,
        detail: Optional[str] = None,
        run_id: Optional[int] = None,
    ) -> None:
        """
        Record an AI matching event to the api_events table.

        Opens its own isolated DB session so event recording never interferes
        with caller's transaction context. Failures are swallowed — event recording
        must never crash the matching flow.

        Args:
            event_type: ApiEventType (reusing NEWS_FETCH for generic API events)
            success: True if the AI match operation succeeded
            detail: JSON-safe string with event context (no secrets, max 500 chars)
            run_id: Optional pipeline run ID (None for out-of-pipeline calls)
        """
        try:
            with SessionLocal() as session:
                event = ApiEvent(
                    event_type=event_type,
                    api_name="ai_matcher",
                    timestamp=datetime.utcnow(),
                    success=success,
                    detail=detail[:500] if detail else None,
                    run_id=run_id,
                )
                session.add(event)
                session.commit()
        except Exception as exc:
            # Never propagate DB errors into the matching flow
            self.logger.warning(
                "ai_matcher_event_record_failed",
                event_type=event_type.value,
                error=str(exc),
            )
