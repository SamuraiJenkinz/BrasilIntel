"""
Pydantic models for insurer matching results.

These models define the response format for the insurer matching service,
supporting both deterministic name-based matching and AI disambiguation.
"""
from pydantic import BaseModel, Field
from typing import Literal


MatchMethod = Literal[
    "deterministic_single",  # Exactly one insurer matched by name/search_term
    "deterministic_multi",   # 2-3 insurers matched deterministically
    "ai_disambiguation",     # AI resolved an ambiguous case
    "unmatched"             # No insurer could be identified
]


class MatchResult(BaseModel):
    """
    Result of matching a news article to insurer(s).

    Used by InsurerMatcher to indicate which insurers are mentioned
    in a given article, along with confidence and method used.
    """

    insurer_ids: list[int] = Field(
        description="Matched insurer IDs (may be empty for unmatched)",
        default_factory=list,
    )
    confidence: float = Field(
        description="Match confidence from 0.0 to 1.0",
        ge=0.0,
        le=1.0,
    )
    method: MatchMethod = Field(
        description="How the match was made"
    )
    reasoning: str = Field(
        description="Brief human-readable explanation of match logic"
    )
