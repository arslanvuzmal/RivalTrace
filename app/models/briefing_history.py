from datetime import datetime
import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from app.core.database import Base

class DeliveryStatus(str, enum.Enum):
    SENT = "SENT"
    FAILED = "FAILED"

class BriefingHistory(Base):
    __tablename__ = "briefing_history"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    competitor_id = Column(Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False)
    scrape_date = Column(DateTime, default=datetime.utcnow)
    
    # Store the JSON payload of the insight. Use JSONB for Postgres, JSON for SQLite fallback.
    insight_json = Column(JSON().with_variant(JSONB, 'postgresql'), nullable=False)
    
    delivery_status = Column(Enum(DeliveryStatus), nullable=False)

    # Relationships
    client = relationship("Client", back_populates="briefing_histories")
    competitor = relationship("Competitor")

    @property
    def competitor_name(self):
        return self.competitor.name if self.competitor else None
