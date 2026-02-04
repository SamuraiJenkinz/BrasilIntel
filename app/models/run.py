"""
Run ORM model for BrasilIntel.

Tracks individual scraping and classification runs.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Run(Base):
    """
    ORM model for scraping/classification runs.

    Tracks execution history with status, timing, and item counts.
    Each run represents a single execution of the news scraping pipeline
    for a specific category (Health, Dental, or Group Life).
    """
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(50), nullable=False)  # Health, Dental, Group Life
    trigger_type = Column(String(20), nullable=False)  # scheduled, manual
    status = Column(String(20), default="pending")  # pending, running, completed, failed

    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    insurers_processed = Column(Integer, default=0)
    items_found = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # Relationships
    news_items = relationship("NewsItem", back_populates="run")

    def __repr__(self) -> str:
        return f"<Run(id={self.id}, category='{self.category}', status='{self.status}')>"
