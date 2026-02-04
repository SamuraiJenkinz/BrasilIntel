"""
Pydantic schemas for report generation.

Includes structured output schemas for Azure OpenAI executive summary generation.
"""
from pydantic import BaseModel, Field
from typing import Literal


class ExecutiveSummary(BaseModel):
    """
    Structured output schema for Azure OpenAI executive summary generation.

    Used with client.beta.chat.completions.parse() for guaranteed schema conformance.
    """
    paragraph: str = Field(
        description="2-3 sentence executive summary in Portuguese highlighting key market developments"
    )
    critical_count: int = Field(
        description="Number of insurers with Critical status in the report"
    )
    watch_count: int = Field(
        description="Number of insurers with Watch status in the report"
    )
    key_theme: Literal["turbulencia", "estabilidade", "crescimento", "consolidacao", "crise", "regulatorio"] = Field(
        description="One-word Portuguese theme summarizing the market situation"
    )


class KeyFinding(BaseModel):
    """Schema for key findings cards in executive summary."""
    severity: Literal["critical", "warning", "positive"] = Field(
        description="Visual severity level for card styling"
    )
    title: str = Field(
        description="Brief title for the finding (max 50 chars)"
    )
    description: str = Field(
        description="1-2 sentence description of the finding"
    )


class ReportContext(BaseModel):
    """Schema for market context items."""
    title: str = Field(
        description="Context item title"
    )
    description: str = Field(
        description="Context item description"
    )
