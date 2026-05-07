"""SQLAlchemy models for Pitch Simulator."""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from database import Base


class ChatSession(Base):
	__tablename__ = 'chat_sessions'

	id = Column(Integer, primary_key=True, index=True)
	session_id = Column(String(255), nullable=False, index=True)
	case_study = Column(String(50), nullable=False, default='template1')
	score = Column(Integer, nullable=False, default=0)
	max_score = Column(Integer, nullable=False, default=0)
	gift_offer = Column(Integer, nullable=False, default=0)
	completed_checkpoints = Column(Text, nullable=False, default='')
	transcript = Column(Text, nullable=False)
	message_count = Column(Integer, nullable=False, default=0)
	created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
