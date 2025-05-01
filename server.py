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
from models import Base, Account, Player

# ⚙️ PostgreSQL Settings (used by server only)
DATABASE_HOST = "75.119.187.81"  # same as SERVER_HOST
DATABASE_NAME = "PyRPG"
DATABASE_USER = "PyRPG_Admin"
DATABASE_PASSWORD = "Christie91!"
DATABASE_URL = f"postgresql+psycopg2://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}/{DATABASE_NAME}"

REQUIRED_VERSION = "v0.0.5"

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
    gold: int
    last_logout_time: str  # ISO 8601 string format

class HeartbeatRequest(BaseModel):
    username: str
    character_name: str
    client_version: str

class LogoutRequest(BaseModel):
    username: str

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

    new_player = Player(
        account_id=account.id,
        name=player_data.get("name", "Unnamed"),
        char_class=player_data.get("char_class", "Warrior"),
        level=player_data.get("level", 1),
        experience=player_data.get("experience", 0),
        gold=player_data.get("gold", 0),  # ✅ ADD THIS!
        inventory=player_data.get("inventory", {}),
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
    character.gold = request.gold
    character.last_logout_time = request.last_logout_time

    db.commit()
    db.refresh(character)

    return {"msg": "Player updated successfully!"}

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
            "gold": p.gold,
            "inventory": p.inventory,
            "equipment": p.equipment,
            "skills": p.skills,
            "username": account.username,
            "role": account.role
        })

    return player_list

@app.get("/chat/fetch")
def fetch_chat_messages(since: float = Query(0.0), player_name: str = Query(...), db: Session = Depends(get_db)):
    messages = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.timestamp > since)
        .filter(
            or_(
                models.ChatMessage.type == "Chat",
                models.ChatMessage.type == "System",
                models.ChatMessage.type == "Admin",
                and_(
                    models.ChatMessage.type == "whisper",
                    models.ChatMessage.sender == player_name
                ),
                and_(
                    models.ChatMessage.type == "whisper",
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
            result.append(character.name)
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

    elif command_text.startswith("/kick"):
        parts = command_text.split()
        if len(parts) < 2:
            return {"success": False, "error": "Usage: /kick <character_name>"}

        target_name = parts[1]
        player = db.query(Player).filter_by(name=target_name, is_active=True).first()
        if not player:
            return {"success": False, "error": f"{target_name} not found or not active."}

        player.is_active = False
        account = db.query(Account).filter_by(id=player.account_id).first()
        if account:
            account.is_online = False
            account.last_seen = datetime.datetime.now(datetime.UTC)

        system_msg = models.ChatMessage(
            sender="System",
            message=f"{target_name} has been kicked by an admin.",
            timestamp=datetime.datetime.now(datetime.UTC).timestamp(),
            type="System"
        )
        db.add(system_msg)
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

        db.commit()
        return {"success": True, "message": f"{target_name} has been muted."}

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

        db.commit()
        return {"success": True, "message": f"{target_name} has been unmuted."}

    elif command == "addcoins":
        if len(parts) < 3:
            return {"success": False, "error": "Usage: /addcoins <character_name> <amount>"}
        target_name = parts[1]
        try:
            amount = int(parts[2])
        except ValueError:
            return {"success": False, "error": "Amount must be a number."}

        player = db.query(Player).filter_by(name=target_name).first()
        if not player:
            return {"success": False, "error": f"Player {target_name} not found."}
        player.gold += amount
        db.commit()
        return {"success": True, "message": f"Added {amount} gold to {target_name}."}

    elif command == "spawnboss":
        if len(parts) < 2:
            return {"success": False, "error": "Usage: /spawnboss <zone>"}
        zone = parts[1]
        # TODO: Implement your boss logic here
        return {"success": True, "message": f"Boss spawned in zone: {zone} (stubbed)"}

    return {"success": False, "error": "Unknown command."}





