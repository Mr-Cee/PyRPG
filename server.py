# server.py
import threading
import time

from fastapi import FastAPI, HTTPException, Depends, Body, Security, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from requests import Session, Request
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from passlib.context import CryptContext
from jose import jwt
import datetime
from pydantic import BaseModel

import models
from models import Base, Account, Player

from settings import DATABASE_URL

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
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(Account).filter_by(username=form_data.username).first()

    if not user or not pwd_context.verify(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password.")

    access_token = create_access_token(data={"sub": user.username})

    # ✅ Register as online
    user.is_online = True
    db.commit()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user.username,
        "role": user.role
    }

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
    db.commit()

    return {"msg": f"Character '{character_name}' set as active for user '{username}'."}

@app.post("/heartbeat")
def heartbeat(data: HeartbeatRequest, db: Session = Depends(get_db)):
    account = db.query(Account).filter_by(username=data.username).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    account.last_seen = datetime.datetime.now(datetime.UTC)
    account.is_online = True

    # Update the character's last seen as well
    player = db.query(Player).filter_by(account_id=account.id, name=data.character_name).first()
    if player:
        player.last_seen = datetime.datetime.now(datetime.UTC)  # Optional: add this column
    else:
        print(f"[Heartbeat] Warning: Character {data.character_name} not found for {data.username}")

    db.commit()
    return {"msg": f"Heartbeat received for {data.username} as {data.character_name}"}

@app.post("/logout/{username}")
def logout(username: str, db: Session = Depends(get_db)):
    user = db.query(Account).filter_by(username=username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_online = False

    # ✅ Deactivate all characters
    characters = db.query(Player).filter_by(account_id=user.id).all()
    for c in characters:
        c.is_active = False

    db.commit()
    return {"msg": f"{username} logged out"}

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
    new_msg = models.ChatMessage(
        sender=chat.sender,
        message=chat.message,
        timestamp=chat.timestamp,
        type=chat.type
    )
    db.add(new_msg)
    db.commit()
    return {"success": True}

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
def fetch_chat_messages(since: float = Query(0.0), db: Session = Depends(get_db)):
    messages = db.query(models.ChatMessage).filter(models.ChatMessage.timestamp > since).order_by(models.ChatMessage.timestamp).all()
    return {
        "messages": [
            {
                "sender": msg.sender,
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





