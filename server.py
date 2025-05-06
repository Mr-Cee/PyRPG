# server.py
import threading
import time
import uuid

from fastapi import FastAPI, HTTPException, Depends, Body, Security, Query, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine, or_, and_
from passlib.context import CryptContext
from jose import jwt
import datetime
from pydantic import BaseModel

import models
from items import create_item
from models import Base, Account, Player

# ⚙️ PostgreSQL Settings (used by server only)
DATABASE_HOST = "75.119.187.81"  # same as SERVER_HOST
DATABASE_NAME = "PyRPG"
DATABASE_USER = "PyRPG_Admin"
DATABASE_PASSWORD = "Christie91!"
DATABASE_URL = f"postgresql+psycopg2://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}/{DATABASE_NAME}"

REQUIRED_VERSION = "v0.0.7"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

app = FastAPI()

SECRET_KEY = "your_super_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

chat_messages = []
online_users = set()
ROLE_HIERARCHY = {
    "player": 0,
    "gm": 1,
    "dev": 2
}
ROLE_COMMANDS = {
    "player": [],
    "gm": ["broadcast", "kick", "mute", "unmute"],
    "dev": ["broadcast", "kick", "mute", "unmute", "createitem", "addcoins", "spawnboss"]
}


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    username: str
    new_password: str

class ChatMessage(BaseModel):
    sender: str
    message: str
    timestamp: float
    type: str = "Chat"  # default to normal chat unless specified

class UpdatePlayerRequest(BaseModel):
    username: str
    name: str
    level: int
    experience: int
    copper: int
    silver: int
    gold: int
    platinum: int
    last_logout_time: str

class HeartbeatRequest(BaseModel):
    username: str
    character_name: str
    client_version: str

class LogoutRequest(BaseModel):
    username: str

class InventoryUpdateRequest(BaseModel):
    character_name: str
    inventory: list

class StatEquipUpdateRequest(BaseModel):
    character_name: str
    stats: dict
    equipment: dict


def create_access_token(data: dict, expires_delta: datetime.timedelta = None):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + (expires_delta or datetime.timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_username(token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Invalid authentication")
    return username

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def background_cleanup_thread():
    while True:
        db = SessionLocal()
        try:
            cutoff = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=2)
            stale_users = db.query(Account).filter(Account.is_online == True, Account.last_seen < cutoff).all()
            for user in stale_users:
                user.is_online = False
                print(f"[Cleanup] Auto-marked {user.username} as offline (last seen: {user.last_seen})")
            db.commit()
        except Exception as e:
            print(f"[Cleanup Error] {e}")
        finally:
            db.close()

        time.sleep(60)  # Run every 60 seconds

def apply_experience_and_level_up(player: Player, xp_gain: int, db: Session = Depends(get_db)):
    player.experience += xp_gain
    while player.experience >= player.level * 25:
        player.experience -= player.level * 25
        player.level += 1
        player.stats["base_health"] = player.stats.get("base_health", 10) + 5
        player.stats["base_mana"] = player.stats.get("base_mana", 10) + 5

        system_msg = models.ChatMessage(
            sender="System",
            recipient=player.name,
            message=f"You leveled up to {player.level}! (+5 Health, +5 Mana)",
            timestamp=datetime.datetime.now(datetime.UTC).timestamp(),
            type="System"
        )
        db.add(system_msg)

def parse_command_arguments(message: str):
    parts = message.split()
    args = {}
    for part in parts[1:]:
        if '=' in part:
            key, value = part.split('=', 1)
            args[key.strip()] = value.strip()
    return args

@app.on_event("startup")
def start_background_cleanup():
    threading.Thread(target=background_cleanup_thread, daemon=True).start()
    print("[Startup] Background cleanup thread started.")

@app.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    username = body.get("username")
    password = body.get("password")
    client_version = body.get("client_version", "unknown")

    # ✅ Enforce version
    if client_version != REQUIRED_VERSION:
        raise HTTPException(
            status_code=426,  # Upgrade Required
            detail=f"Client version '{client_version}' is outdated. Please update to '{REQUIRED_VERSION}'."
        )

    user = db.query(Account).filter_by(username=username).first()
    if not user or not pwd_context.verify(password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password.")

    access_token = create_access_token(data={"sub": username})
    user.is_online = True
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role
    }

@app.post("/logout")
def logout(payload: LogoutRequest, db: Session = Depends(get_db)):
    account = db.query(Account).filter_by(username=payload.username).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.is_online = False
    account.last_seen = datetime.datetime.now(datetime.UTC)

    # ✅ Deactivate active character
    active_player = db.query(Player).filter_by(account_id=account.id, is_active=True).first()
    if active_player:
        active_player.is_active = False
        active_player.last_seen = datetime.datetime.now(datetime.UTC)

    db.commit()
    return {"msg": f"{payload.username} logged out successfully."}

@app.post("/set_active_character")
def set_active_character(username: str = Body(...), character_name: str = Body(...), db: Session = Depends(get_db)):
    account = db.query(Account).filter_by(username=username).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found.")

    # Deactivate all characters
    db.query(Player).filter_by(account_id=account.id).update({"is_active": False})

    # Activate selected one
    character = db.query(Player).filter_by(account_id=account.id, name=character_name).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found.")

    character.is_active = True
    character.last_seen = datetime.datetime.now(datetime.UTC)  # ✅ mark character seen
    account.is_online = True  # ✅ mark account as online
    account.last_seen = datetime.datetime.now(datetime.UTC)  # ✅ set last_seen immediately

    # Send system broadcast when character logs in
    broadcast = models.ChatMessage(
        sender="System",
        message=f"{character.name} has entered the world.",
        timestamp=datetime.datetime.now(datetime.UTC).timestamp(),
        type="System"
    )
    db.add(broadcast)

    db.commit()

    return {"msg": f"Character '{character_name}' set as active for user '{username}'."}

@app.post("/heartbeat")
def heartbeat(data: HeartbeatRequest, db: Session = Depends(get_db)):
    if data.client_version != REQUIRED_VERSION:
        raise HTTPException(
            status_code=426,  # Upgrade Required
            detail=f"Client version '{data.client_version}' is outdated. Please update to '{REQUIRED_VERSION}'."
        )

    account = db.query(Account).filter_by(username=data.username).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.last_seen = datetime.datetime.now(datetime.UTC)
    account.is_online = True

    player = db.query(Player).filter_by(account_id=account.id, name=data.character_name).first()
    if player:
        player.last_seen = datetime.datetime.now(datetime.UTC)

    db.commit()
    return {"msg": f"Heartbeat OK: {data.username} on {data.client_version}"}

@app.post("/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    existing_user = db.query(Account).filter_by(username=request.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered.")

    hashed_password = pwd_context.hash(request.password)
    new_account = Account(
        username=request.username,
        password_hash=hashed_password,
        email=request.email,
        role="player" )

    db.add(new_account)
    db.commit()
    db.refresh(new_account)

    return {"msg": "Registration successful."}

@app.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Session = Depends(get_db)):
    account = db.query(Account).filter_by(email=request.email).first()
    if not account:
        raise HTTPException(status_code=404, detail="Email not found.")

    return {"msg": "Email found.", "username": account.username}

@app.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    account = db.query(Account).filter_by(username=request.username).first()
    if not account:
        raise HTTPException(status_code=404, detail="Username not found.")

    hashed_password = pwd_context.hash(request.new_password)
    account.password_hash = hashed_password

    db.commit()

    return {"msg": "Password reset successfully."}

@app.post("/player/{username}")
def create_player(username: str, player_data: dict = Body(...), token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):


    account = db.query(Account).filter_by(username=username).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found.")

    # Check if a player with that name already exists for this account
    existing_player = db.query(Player).filter_by(account_id=account.id, name=player_data["name"]).first()
    if existing_player:
        raise HTTPException(status_code=400, detail="Character name already exists for this account.")

    raw_inventory = player_data.get("inventory", [])
    inventory = raw_inventory if isinstance(raw_inventory, list) else []


    new_player = Player(
        account_id=account.id,
        name=player_data.get("name", "Unnamed"),
        char_class=player_data.get("char_class", "Warrior"),
        level=player_data.get("level", 1),
        experience=player_data.get("experience", 0),
        copper=player_data.get("copper", 0),
        silver=player_data.get("silver", 0),
        gold=player_data.get("gold", 0),
        platinum=player_data.get("platinum", 0),
        stats=player_data.get("stats", {
            "Health": 10,
            "Mana": 10,
            "base_health": 10,
            "base_mana": 10,
            "Strength": 5,
            "Dexterity": 5,
            "Intelligence": 5,
            "Vitality": 5,
            "Critical Chance": 0,
            "Critical Damage": 0,
            "Armor": 0,
            "Block": 0,
            "Dodge": 0,
            "Attack Speed": 1.0
        }),
        inventory=inventory,
        max_inventory_slots=player_data.get("max_inventory_slots", 36),
        equipment=player_data.get("equipment", {}),
        skills=player_data.get("skills", {})
    )

    db.add(new_player)
    db.commit()
    db.refresh(new_player)

    return {"msg": "Player created successfully!"}

@app.post("/update_player")
def update_player(request: UpdatePlayerRequest, db: Session = Depends(get_db)):

    account = db.query(Account).filter_by(username=request.username).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found.")

    character = db.query(Player).filter_by(account_id=account.id, name=request.name).first()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found.")

    character.level = request.level
    character.experience = request.experience
    character.copper = request.copper
    character.silver = request.silver
    character.gold = request.gold
    character.platinum = request.platinum
    character.last_logout_time = request.last_logout_time

    db.commit()
    db.refresh(character)

    return {"msg": "Player updated successfully!"}

@app.post("/inventory/update")
def update_inventory(request: InventoryUpdateRequest, db: Session = Depends(get_db)):
    player = db.query(Player).filter_by(name=request.character_name).first()
    if not player:
        raise HTTPException(status_code=404, detail="Character not found.")

    player.inventory = request.inventory
    db.commit()

    return {"success": True, "message": f"Inventory updated for {request.character_name}."}

@app.post("/stats_equipment/update")
def update_stats_and_equipment(request: StatEquipUpdateRequest, db: Session = Depends(get_db)):
    player = db.query(Player).filter_by(name=request.character_name).first()
    if not player:
        raise HTTPException(status_code=404, detail="Character not found.")

    player.stats = request.stats
    player.equipment = request.equipment
    db.commit()
    return {"success": True, "message": f"Stats and equipment updated for {request.character_name}."}

@app.post("/add_experience")
def add_experience(payload: dict, db: Session = Depends(get_db)):
    requester = payload.get("requester")
    target = payload.get("target")
    amount = payload.get("amount")

    if not all([requester, target, amount]):
        return {"success": False, "error": "Missing parameters."}

    try:
        amount = int(amount)
    except ValueError:
        return {"success": False, "error": "Amount must be an integer."}

    target_player = db.query(Player).filter_by(name=target, is_active=True).first()
    if not target_player:
        return {"success": False, "error": f"{target} is not online or doesn't exist."}

    apply_experience_and_level_up(target_player, amount)
    db.commit()

    system_msg = models.ChatMessage(
        sender="System",
        recipient=target_player.name,
        message=f"You gained {amount} XP! Your new level is {target_player.level}.",
        timestamp=datetime.datetime.now(datetime.UTC).timestamp(),
        type="System"
    )
    db.add(system_msg)

    return {
        "success": True,
        "message": f"{target} gained {amount} XP (level: {target_player.level}).",
        "level": target_player.level,
        "experience": target_player.experience,
        "stats": target_player.stats
    }

@app.post("/add_coins")
def add_coins(payload: dict, db: Session = Depends(get_db)):
    requester = payload.get("requester")
    amount = payload.get("amount")
    coin_type = payload.get("coin_type", "").lower()
    target_name = payload.get("target")

    if not all([requester, amount, coin_type]):
        return {"success": False, "error": "Missing parameters."}

    if coin_type not in ("copper", "silver", "gold", "platinum"):
        return {"success": False, "error": "Invalid coin type. Must be copper, silver, gold, or platinum."}

    try:
        amount = int(amount)
    except ValueError:
        return {"success": False, "error": "Amount must be a number."}

    if not target_name:
        # Get active character for the requester
        account = db.query(Account).filter_by(username=requester).first()
        if not account:
            return {"success": False, "error": "Requester account not found."}
        target_player = db.query(Player).filter_by(account_id=account.id, is_active=True).first()
    else:
        target_player = db.query(Player).filter_by(name=target_name).first()

    if not target_player:
        return {"success": False, "error": f"Player {target_name or requester} not found."}

    current = getattr(target_player, coin_type, 0)
    setattr(target_player, coin_type, current + amount)
    db.commit()

    return {
        "success": True,
        "message": f"Added {amount} {coin_type} to {target_player.name}."
    }

@app.post("/createitem")
def create_item_endpoint(data: dict, db: Session = Depends(get_db)):
    required = ["slot_type"]
    for key in required:
        if key not in data:
            return {"success": False, "error": f"Missing field: {key}"}

    slot_type = data["slot_type"]
    char_class = data.get("char_class", "Warrior")
    rarity = data.get("rarity")
    weapon_type = data.get("weapon_type")
    item_level = int(data.get("item_level", 1))
    target_name = data.get("target")

    # Normalize weapon type capitalization
    if weapon_type:
        weapon_type = weapon_type.capitalize()
    # Normalize rarity capitalization
    if rarity:
        rarity = rarity.capitalize()

    item = create_item(slot_type, char_class, rarity, weapon_type=weapon_type, item_level=item_level)
    print(item)

    item["slot"] = None  # Inventory will auto-place it

    target = db.query(Player).filter_by(name=target_name).first()
    if not target:
        return {"success": False, "error": f"Target {target_name} not found"}

    # Load current inventory
    inventory = target.inventory or []

    # Determine used slots
    used_slots = {itm.get("slot") for itm in inventory if isinstance(itm.get("slot"), int)}
    max_slots = target.max_inventory_slots or 36
    all_slots = set(range(max_slots))
    free_slots = list(all_slots - used_slots)

    if not free_slots:
        return {"success": False, "error": "Target inventory is full"}

    # Assign the first free slot
    item["slot"] = free_slots[0]


    inventory.append(item)
    target.inventory = inventory
    db.commit()
    db.refresh(target)

    # ✅ Send system whisper to muted player
    system_msg = models.ChatMessage(
        sender="InventoryUpdate",
        recipient=target_name,
        message=f"{item['name']} added to {target.name}'s inventory.",
        timestamp=datetime.datetime.now(datetime.UTC).timestamp(),
        type="InventoryUpdate"
    )
    db.add(system_msg)
    db.commit()


    return {"success": True,
            "message": f"{item['name']} added to {target.name}'s inventory.",
            "item": item}

@app.post("/chat/send")
def send_chat_message(chat: ChatMessage):
    db = SessionLocal()

    player = db.query(Player).filter_by(name=chat.sender, is_active=True).first()
    if not player:
        return {"success": False, "error": "Sender not found."}

    if player.is_muted:
        system_msg = models.ChatMessage(
            sender="System",
            message="You have been muted. Please contact a GM to resolve this issue.\n User /gms to find any GMs online right now",
            timestamp=datetime.datetime.now(datetime.UTC).timestamp(),
            type="System",
            recipient=player.name  # Only this player receives it
        )
        db.add(system_msg)
        db.commit()
        return {"success": False, "error": "Muted"}

    new_msg = models.ChatMessage(
        sender=chat.sender,
        message=chat.message,
        timestamp=chat.timestamp,
        type=chat.type
    )
    db.add(new_msg)
    db.commit()
    return {"success": True}

@app.post("/whisper")
def send_whisper(payload: dict, db: Session = Depends(get_db)):
    sender_name = payload.get("sender")
    recipient_name = payload.get("recipient")
    message = payload.get("message")

    # Check if recipient is online
    recipient_player = db.query(models.Player).filter_by(name=recipient_name, is_active=True).first()
    if not recipient_player:
        return {"success": False, "error": f"{recipient_name} is not online."}

    recipient_account = db.query(models.Account).filter_by(id=recipient_player.account_id).first()
    if not recipient_account or not recipient_account.is_online:
        return {"success": False, "error": f"{recipient_name} is not online."}

    # Store message as a private ChatMessage (or handle separately if needed)
    whisper_message = models.ChatMessage(
        sender=sender_name,
        recipient=recipient_name,
        message=message,
        timestamp=time.time(),
        type="whisper"
    )
    db.add(whisper_message)
    db.commit()

    return {"success": True}

@app.get("/required_version")
def get_required_version():
    return { "version": REQUIRED_VERSION, "download_url": f"https://github.com/Mr-Cee/PyRPG/releases/download/{REQUIRED_VERSION}/update_package.zip" }

@app.get("/player/{username}")
def get_players(username: str, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    account = db.query(Account).filter_by(username=username).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found.")

    players = db.query(Player).filter_by(account_id=account.id).all()

    player_list = []
    for p in players:
        player_list.append({
            "name": p.name,
            "char_class": p.char_class,
            "level": p.level,
            "experience": p.experience,
            "coins": {
                "copper": p.copper,
                "silver": p.silver,
                "gold": p.gold,
                "platinum": p.platinum
            },
            "inventory": p.inventory,
            "equipment": p.equipment,
            "skills": p.skills,
            "username": account.username,
            "role": account.role,
            "is_muted": p.is_muted
        })

    return player_list

@app.get("/player_stats")
def get_player_stats(requester_name: str, target_name: str = None, db: Session = Depends(get_db)):
    if target_name is None:
        target_name = requester_name

    player = db.query(Player).filter_by(name=target_name).first()
    if not player:
        raise HTTPException(status_code=404, detail="Character not found.")

        # Build total_stats with gear bonuses
    total_stats = player.stats.copy() if player.stats else {}

    # Add equipment stat bonuses
    if player.equipment:
        for item in player.equipment.values():
            if item and isinstance(item, dict):
                for stat, value in item.get("stats", {}).items():
                    total_stats[stat] = total_stats.get(stat, 0) + value

    # Derived stats
    strength = total_stats.get("Strength", 0)
    intelligence = total_stats.get("Intelligence", 0)
    dexterity = total_stats.get("Dexterity", 0)
    vitality = total_stats.get("Vitality", 0)

    total_stats["Bonus Damage"] = strength // 5
    total_stats["Bonus Mana"] = intelligence // 5
    total_stats["Bonus Health"] = vitality // 5
    total_stats["Avoidance"] = dexterity // 10
    total_stats["Health"] = total_stats["base_health"] + vitality // 5
    total_stats["Mana"] = total_stats["base_mana"] + intelligence // 5
    total_stats["Avoidance"] = intelligence // 10
    total_stats["Dodge"] = dexterity // 10

    return {
        "name": player.name,
        "char_class": player.char_class,
        "level": player.level,
        "experience": player.experience,
        "coins": {
            "copper": player.copper,
            "silver": player.silver,
            "gold": player.gold,
            "platinum": player.platinum
        },
        "base_stats": player.stats if hasattr(player, "stats") else {},
        "total_stats": total_stats,
        "equipment": player.equipment,
        "is_muted": player.is_muted
    }

@app.get("/player_coins")
def get_player_coins(requester_name: str, db: Session = Depends(get_db)):
    player = db.query(Player).filter_by(name=requester_name).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return {
        "copper": player.copper,
        "silver": player.silver,
        "gold": player.gold,
        "platinum": player.platinum
    }

@app.get("/chat/fetch")
def fetch_chat_messages(since: float = Query(0.0), player_name: str = Query(...), db: Session = Depends(get_db)):
    messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.timestamp > since)
        .filter(
            or_(
                models.ChatMessage.type == "Chat",
                models.ChatMessage.type == "Admin",
                and_(
                    models.ChatMessage.type == "System",
                    or_(
                        models.ChatMessage.recipient == None,
                        models.ChatMessage.recipient == player_name
                    )
                ),
                and_(
                    models.ChatMessage.type == "whisper",
                    models.ChatMessage.sender == player_name
                ),
                and_(
                    models.ChatMessage.type == "whisper",
                    models.ChatMessage.recipient == player_name
                ),
                and_(
                    models.ChatMessage.type == "InventoryUpdate",
                    models.ChatMessage.recipient == player_name
                )
            )
        )
        .order_by(models.ChatMessage.timestamp)
        .all()
    )

    return {
        "messages": [
            {
                "sender": msg.sender,
                "recipient": getattr(msg, "recipient", None),
                "message": msg.message,
                "timestamp": msg.timestamp,
                "type": msg.type
            } for msg in messages
        ]
    }

@app.get("/chat/recent")
def fetch_recent_messages(limit: int = 25, db: Session = Depends(get_db)):
    messages = db.query(models.ChatMessage).order_by(models.ChatMessage.timestamp.desc()).limit(limit).all()
    return {
        "messages": [
            {
                "sender": msg.sender,
                "message": msg.message,
                "timestamp": msg.timestamp,
                "type": msg.type
            } for msg in reversed(messages)
        ]
    }

@app.get("/online_players")
def get_online_players(db: Session = Depends(get_db)):
    now = datetime.datetime.now(datetime.UTC)
    cutoff = now - datetime.timedelta(minutes=2)

    accounts = db.query(Account).filter(Account.is_online == True, Account.last_seen >= cutoff).all()
    result = []

    for account in accounts:
        character = db.query(Player).filter_by(account_id=account.id, is_active=True).first()
        if character:
            result.append({
                "name": character.name,
                "is_muted": character.is_muted
            })
        else:
            result.append(f"[No Active Character for {account.username}]")

    return {"online": result}

@app.get("/online_gms")
def get_online_gms(db: Session = Depends(get_db)):
    gm_roles = ["gm", "dev"]
    online_gms = (
        db.query(models.Player)
        .join(models.Account, models.Account.id == models.Player.account_id)
        .filter(
            models.Player.is_active == True,
            models.Account.is_online == True,
            models.Account.role.in_(gm_roles)
        )
        .all()
    )
    gm_names = [gm.name for gm in online_gms]
    return {"success": True, "gms": gm_names}

@app.get("/online_staff")
def get_online_staff(db: Session = Depends(get_db)):
    staff_roles = ["gm", "dev"]
    staff = (
        db.query(models.Player.name, models.Account.role)
        .join(models.Account, models.Account.id == models.Player.account_id)
        .filter(
            models.Player.is_active == True,
            models.Account.is_online == True,
            models.Account.role.in_(staff_roles)
        )
        .all()
    )

    formatted = [f"{name} ({role})" for name, role in staff]
    return {"success": True, "staff": formatted}

@app.post("/report")
def submit_report(payload: dict, db: Session = Depends(get_db)):
    sender = payload.get("sender")
    message = payload.get("message", "").strip()

    if not sender or not message:
        return {"success": False, "error": "Missing sender or message."}

    # Create persistent case
    report = models.ReportCase(sender=sender, message=message)
    db.add(report)
    db.commit()
    db.refresh(report)

    # Broadcast to online GMs/Devs in Admin tab
    timestamp = datetime.datetime.now(datetime.UTC).timestamp()
    staff = (
        db.query(models.Player.name)
        .join(models.Account, models.Account.id == models.Player.account_id)
        .filter(
            models.Player.is_active == True,
            models.Account.is_online == True,
            models.Account.role.in_(["gm", "dev"])
        )
        .all()
    )

    new_msg = models.ChatMessage(
        id=str(uuid.uuid4()),
        sender="Report",
        recipient="Admin",  # Not targeting a player, but tagged as admin
        message=f"[Report] from {sender}: {message}",
        timestamp=time.time(),
        type="Admin"  # So it only shows in admin tab
    )
    db.add(new_msg)
    db.commit()
    return {"success": True}

@app.get("/my_reports")
def get_my_reports(player_name: str, db: Session = Depends(get_db)):
    reports = db.query(models.ReportCase).filter_by(sender=player_name).order_by(
        models.ReportCase.timestamp.asc()).all()
    return [r.to_dict() for r in reports]

@app.get("/reports_view")
def reports_view(db: Session = Depends(get_db)):
    cases = db.query(models.ReportCase).filter(models.ReportCase.status == "open").order_by(models.ReportCase.timestamp.desc()).all()

    return {
        "success": True,
        "reports": [
            {
                "id": case.id,
                "sender": case.sender,
                "message": case.message,
                "timestamp": case.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            } for case in cases
        ]
    }

@app.get("/inventory/{character_name}")
def get_inventory(character_name: str, db: Session = Depends(get_db)):
    player = db.query(Player).filter_by(name=character_name).first()
    if not player:
        return []

    return player.inventory  # This assumes it's a JSON-serializable list

@app.post("/report_resolve")
def resolve_report(payload: dict, db: Session = Depends(get_db)):
    case_id = payload.get("case_id")
    resolution = payload.get("resolution", "")

    case = db.query(models.ReportCase).filter(models.ReportCase.id == case_id).first()
    if not case:
        return {"success": False, "error": "Report not found."}
    if case.status == "closed":
        return {"success": False, "error": "Report already resolved."}

    case.status = "closed"
    case.resolution = resolution
    db.commit()

    return {"success": True, "message": f"Report Case #{case_id} resolved with message: {resolution}"}

@app.delete("/player/{username}")
def delete_player(username: str, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    account = db.query(Account).filter_by(username=username).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found.")

    player = db.query(Player).filter_by(account_id=account.id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found.")

    db.delete(player)
    db.commit()

    return {"msg": "Player deleted successfully."}

@app.delete("/account/{username}")
def delete_account(username: str, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):

    account = db.query(Account).filter_by(username=username).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found.")

    # ✅ Delete associated players first
    players = db.query(Player).filter_by(account_id=account.id).all()
    for player in players:
        db.delete(player)

    db.flush()  # ✅ Force delete of players first

    # ✅ Then delete account
    db.delete(account)

    db.commit()

    return {"msg": "Account and associated players deleted successfully."}

@app.post("/admin_command")
def admin_command(payload: dict, db: Session = Depends(get_db)):
    username = payload.get("username")
    command_text = payload.get("command", "").strip()
    account = db.query(Account).filter_by(username=username).first()

    if not account:
        return {"success": False, "error": "Account not found."}

    # Extract actual command word (e.g., "kick" from "/kick ...")
    parts = command_text.split()
    if not parts:
        return {"success": False, "error": "Empty command."}
    command = parts[0].lstrip("/")

    # Permission check
    allowed_commands = ROLE_COMMANDS.get(account.role, [])
    if command not in allowed_commands:
        return {"success": False, "error": f"Permission denied for command: /{command}"}


    # ✅ Step 2: Parse command
    if command_text.startswith("/broadcast"):
        parts = command_text.split(maxsplit=1)
        if len(parts) < 2:
            return {"success": False, "error": "Usage: /broadcast <message>"}

        message = parts[1]
        broadcast = models.ChatMessage(
            sender="System",
            message=f"[Admin] {message}",
            timestamp=datetime.datetime.now(datetime.UTC).timestamp(),
            type="System"
        )
        db.add(broadcast)
        db.commit()
        return {"success": True, "message": "Broadcast sent."}

    elif command == "kick":
        parts = command_text.split()
        if len(parts) < 2:
            return {"success": False, "error": "Usage: /kick <character_name>"}

        target_name = parts[1]
        player = db.query(Player).filter_by(name=target_name, is_active=True).first()
        if not player:
            return {"success": False, "error": f"{target_name} not found or not active."}

        account = db.query(Account).filter_by(id=player.account_id).first()
        if account:
            account.is_online = False
            account.last_seen = datetime.datetime.now(datetime.UTC)

        player.is_active = False

        # ✅ System whisper to the kicked player
        kick_msg = models.ChatMessage(
            sender="System",
            recipient=player.name,
            message="[kick] You have been kicked by an admin.",
            timestamp=datetime.datetime.now(datetime.UTC).timestamp(),
            type="System"
        )
        db.add(kick_msg)

        db.commit()

        return {"success": True, "message": f"{target_name} kicked."}

    elif command == "mute":
        if len(parts) < 2:
            return {"success": False, "error": "Usage: /mute <character_name>"}
        target_name = parts[1]
        player = db.query(Player).filter_by(name=target_name).first()
        if not player:
            return {"success": False, "error": f"Player {target_name} not found."}
        player.is_muted = True

        # ✅ Send system whisper to muted player
        system_msg = models.ChatMessage(
            sender="System",
            recipient=player.name,
            message="You have been muted by a GM. You will not be able to chat until unmuted.",
            timestamp=datetime.datetime.now(datetime.UTC).timestamp(),
            type="System"
        )
        db.add(system_msg)
        # ✅ Send system whisper to muted player
        admin_msg = models.ChatMessage(
            sender="Admin",
            recipient=player.name,
            message=f"{target_name} has been muted.",
            timestamp=datetime.datetime.now(datetime.UTC).timestamp(),
            type="Admin"
        )
        db.add(admin_msg)

        db.commit()
        return {"success": True}

    elif command == "unmute":
        if len(parts) < 2:
            return {"success": False, "error": "Usage: /unmute <character_name>"}
        target_name = parts[1]
        player = db.query(Player).filter_by(name=target_name).first()
        if not player:
            return {"success": False, "error": f"Player {target_name} not found."}
        player.is_muted = False

        # ✅ Send system whisper to unmuted player
        system_msg = models.ChatMessage(
            sender="System",
            recipient=player.name,
            message="You have been unmuted by a GM. You can now chat again.",
            timestamp=datetime.datetime.now(datetime.UTC).timestamp(),
            type="System"
        )
        db.add(system_msg)

        # ✅ Send system whisper to unmuted player
        system_msg = models.ChatMessage(
            sender="Admin",
            recipient=player.name,
            message=f"{target_name} has been unmuted.",
            timestamp=datetime.datetime.now(datetime.UTC).timestamp(),
            type="Admin"
        )
        db.add(system_msg)

        db.commit()
        return {"success": True}

    elif command == "spawnboss":
        if len(parts) < 2:
            return {"success": False, "error": "Usage: /spawnboss <zone>"}
        zone = parts[1]
        # TODO: Implement your boss logic here
        return {"success": True, "message": f"Boss spawned in zone: {zone} (stubbed)"}

    return {"success": False, "error": "Unknown command."}





