# models.py

import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, Float, Boolean
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

class ChatMessage(Base):
    __tablename__ = 'chat_messages'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender = Column(String, nullable=False)
    message = Column(String, nullable=False)
    timestamp = Column(Float, nullable=False)
    type = Column(String, nullable=False, default="Chat")
