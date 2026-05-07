from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)

    session_id = Column(String, nullable=False)
    case_study = Column(String)
    score = Column(Integer)
    max_score = Column(Integer)
    gift_offer = Column(Integer)

    completed_checkpoints = Column(Text)
    transcript = Column(Text)

    message_count = Column(Integer)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

