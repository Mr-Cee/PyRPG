# models.py
import datetime
import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, Float, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Account(Base):
    __tablename__ = 'accounts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    role = Column(String, default="player")
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime, default=datetime.datetime.now(datetime.UTC))

class Player(Base):
    __tablename__ = 'players'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey('accounts.id'), nullable=False)
    name = Column(String, nullable=False)
    char_class = Column(String, nullable=False)
    level = Column(Integer, default=1)
    experience = Column(Integer, default=0)
    gold = Column(Integer, default=0)  # ✅ Add this
    last_logout_time = Column(String, nullable=True)  # ✅ Add this, store ISO string
    inventory = Column(JSONB, default=dict)
    equipment = Column(JSONB, default=dict)
    skills = Column(JSONB, default=dict)
    is_active = Column(Boolean, default=False)
    is_muted = Column(Boolean, default=False)

class ChatMessage(Base):
    __tablename__ = 'chat_messages'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender = Column(String, nullable=False)
    recipient = Column(String, nullable=True)
    message = Column(String, nullable=False)
    timestamp = Column(Float, nullable=False)
    type = Column(String, nullable=False, default="Chat")

class ReportCase(Base):
    __tablename__ = "report_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sender = Column(String, nullable=False)
    message = Column(String, nullable=False)
    status = Column(String, default="open")  # "open" or "closed"
    resolution = Column(Text, nullable=True)  # ✅ New column for resolution message
    timestamp = Column(DateTime, default=datetime.datetime.now(datetime.UTC))

    def to_dict(self):
        return {
            "id": self.id,
            "sender": self.sender,
            "message": self.message,
            "timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S") if self.timestamp else None,
            "resolved": self.status,
            "resolution_message": self.resolution_message
        }

