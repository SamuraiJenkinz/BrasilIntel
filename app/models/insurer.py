"""
Insurer ORM model for BrasilIntel.

Represents monitored insurance companies in the Brazilian market.
"""
from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
    Index
)
from sqlalchemy.orm import relationship
from app.database import Base


class Insurer(Base):
    """
    ORM model for insurers (insurance companies).

    ANS code is the unique identifier assigned by Brazil's National
    Supplementary Health Agency (Agencia Nacional de Saude Suplementar).
    """
    __tablename__ = "insurers"
    __table_args__ = (
        UniqueConstraint("ans_code", name="uix_ans_code"),
        Index("ix_insurers_name", "name"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    ans_code = Column(String(6), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    cnpj = Column(String(18), nullable=True)
    category = Column(String(50), nullable=False)  # Health, Dental, Group Life
    market_master = Column(String(255), nullable=True)
    status = Column(String(50), nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    search_terms = Column(String(500), nullable=True)  # Custom search terms per DATA-03
    created_at = Column(DateTime, default=datetime.utcnow, nullable=True)
    updated_at = Column(DateTime, onupdate=datetime.utcnow, nullable=True)

    # Relationships
    news_items = relationship("NewsItem", back_populates="insurer")

    def __repr__(self) -> str:
        return f"<Insurer(id={self.id}, ans_code='{self.ans_code}', name='{self.name}')>"
