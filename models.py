# models.py
import datetime
import uuid
import enum
from sqlalchemy import Column, String, Integer, ForeignKey, Float, Boolean, DateTime, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import relationship

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

class GatheringActivityEnum(enum.Enum):
    none = "none"
    woodcutting = "woodcutting"
    mining = "mining"
    farming = "farming"
    scavenging = "scavenging"

class Player(Base):
    __tablename__ = 'players'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey('accounts.id'), nullable=False)
    name = Column(String, nullable=False)
    char_class = Column(String, nullable=False)
    level = Column(Integer, default=1)
    experience = Column(Integer, default=0)
    copper = Column(Integer, default=0)
    silver = Column(Integer, default=0)
    gold = Column(Integer, default=0)
    platinum = Column(Integer, default=0)
    last_logout_time = Column(String, nullable=True)  # ✅ Add this, store ISO string
    max_inventory_slots = Column(Integer, default=36)
    inventory = Column(MutableList.as_mutable(JSONB), default=dict)
    equipment = Column(JSONB, default=dict)
    stats = Column(JSONB, default=dict)
    skills = Column(JSONB, default=dict)
    is_active = Column(Boolean, default=False)
    is_muted = Column(Boolean, default=False)
    highest_dungeon_completed = Column(Integer, default=0)
    best_dungeon_time_seconds = Column(Integer, default=0)

    current_gathering_activity = Column(SqlEnum(GatheringActivityEnum), default=GatheringActivityEnum.none)
    gathering_start_time = Column(DateTime, nullable=True)

    woodcutting_level = Column(Integer, default=1)
    mining_level = Column(Integer, default=1)
    farming_level = Column(Integer, default=1)
    scavenging_level = Column(Integer, default=1)
    gathered_materials = relationship("GatheredMaterial", back_populates="player")

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
            "resolution_message": self.resolution
        }

class ServerConfig(Base):
    __tablename__ = "server_config"
    id = Column(Integer, primary_key=True, autoincrement=True)
    login_banner = Column(Text, default="")
    last_updated = Column(DateTime, default=datetime.datetime.now(datetime.UTC))
    patch_notes = Column(Text, default="")

class GatheredMaterial(Base):
    __tablename__ = "gathered_materials"
    id = Column(Integer, primary_key=True)
    player = relationship("Player", back_populates="gathered_materials")
    player_id = Column(UUID(as_uuid=True), ForeignKey("players.id"))
    item_id = Column(Integer)
    quantity = Column(Integer, default=0)
    name = Column(String, default="")
    rarity = Column(String, default="")


