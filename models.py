# models.py

import uuid
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Account(Base):
    __tablename__ = 'accounts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)

class Player(Base):
    __tablename__ = 'players'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey('accounts.id'), nullable=False)
    name = Column(String, nullable=False)
    char_class = Column(String, nullable=False)
    level = Column(Integer, default=1)
    experience = Column(Integer, default=0)
    inventory = Column(JSONB, default=dict)    # Store as JSON blob
    equipment = Column(JSONB, default=dict)
    skills = Column(JSONB, default=dict)
