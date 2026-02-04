"""
Pydantic schemas for Insurer validation.

Provides request/response validation for insurer API endpoints.
"""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class InsurerBase(BaseModel):
    """Base schema with shared insurer fields and validation rules."""
    ans_code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit ANS registration code"
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Official company name"
    )
    cnpj: str | None = Field(
        default=None,
        max_length=18,
        description="Brazilian tax ID (CNPJ) formatted as XX.XXX.XXX/XXXX-XX"
    )
    category: str = Field(
        ...,
        pattern=r"^(Health|Dental|Group Life)$",
        description="Insurer category: Health, Dental, or Group Life"
    )
    market_master: str | None = Field(
        default=None,
        max_length=255,
        description="Parent company or market master name"
    )
    status: str | None = Field(
        default=None,
        max_length=50,
        description="Operational status"
    )
    search_terms: str | None = Field(
        default=None,
        max_length=500,
        description="Custom search terms for news monitoring"
    )


class InsurerCreate(InsurerBase):
    """Schema for creating a new insurer."""
    enabled: bool = Field(
        default=True,
        description="Whether to include in monitoring"
    )


class InsurerUpdate(BaseModel):
    """Schema for updating an insurer (PATCH - all fields optional)."""
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Official company name"
    )
    enabled: bool | None = Field(
        default=None,
        description="Whether to include in monitoring"
    )
    search_terms: str | None = Field(
        default=None,
        max_length=500,
        description="Custom search terms for news monitoring"
    )


class InsurerResponse(InsurerBase):
    """Schema for insurer API responses."""
    id: int = Field(..., description="Database primary key")
    enabled: bool = Field(..., description="Whether included in monitoring")
    created_at: datetime | None = Field(
        default=None,
        description="Record creation timestamp"
    )
    updated_at: datetime | None = Field(
        default=None,
        description="Last update timestamp"
    )

    model_config = ConfigDict(from_attributes=True)
