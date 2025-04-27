# server.py

from fastapi import FastAPI, HTTPException, Depends, Body, Security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from passlib.context import CryptContext
from jose import jwt
import datetime
from pydantic import BaseModel

from models import Base, Account, Player

DATABASE_URL = "postgresql+psycopg2://PyRPG_Admin:Christie91!@localhost/PyRPG"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

app = FastAPI()

SECRET_KEY = "your_super_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    username: str
    new_password: str

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

@app.post("/register")
def register(request: RegisterRequest):
    db = SessionLocal()
    existing_user = db.query(Account).filter_by(username=request.username).first()
    if existing_user:
        db.close()
        raise HTTPException(status_code=400, detail="Username already registered.")

    hashed_password = pwd_context.hash(request.password)
    new_account = Account(username=request.username, password_hash=hashed_password, email=request.email)

    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    db.close()

    return {"msg": "Registration successful."}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    user = db.query(Account).filter_by(username=form_data.username).first()
    db.close()
    if not user or not pwd_context.verify(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password.")

    access_token = create_access_token(data={"sub": user.username})

    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/player/{username}")
def get_players(username: str, token: str = Depends(oauth2_scheme)):
    db = SessionLocal()

    account = db.query(Account).filter_by(username=username).first()
    if not account:
        db.close()
        raise HTTPException(status_code=404, detail="Account not found.")

    players = db.query(Player).filter_by(account_id=account.id).all()

    player_list = []
    for p in players:
        player_list.append({
            "name": p.name,
            "char_class": p.char_class,
            "level": p.level,
            "experience": p.experience,
            "inventory": p.inventory,
            "equipment": p.equipment,
            "skills": p.skills
        })

    db.close()

    return player_list

@app.post("/player/{username}")
def create_player(username: str, player_data: dict = Body(...), token: str = Depends(oauth2_scheme)):
    db = SessionLocal()

    account = db.query(Account).filter_by(username=username).first()
    if not account:
        db.close()
        raise HTTPException(status_code=404, detail="Account not found.")

    # Check if a player with that name already exists for this account
    existing_player = db.query(Player).filter_by(account_id=account.id, name=player_data["name"]).first()
    if existing_player:
        db.close()
        raise HTTPException(status_code=400, detail="Character name already exists for this account.")

    new_player = Player(
        account_id=account.id,
        name=player_data.get("name", "Unnamed"),
        char_class=player_data.get("char_class", "Warrior"),
        level=player_data.get("level", 1),
        experience=player_data.get("experience", 0),
        inventory=player_data.get("inventory", {}),
        equipment=player_data.get("equipment", {}),
        skills=player_data.get("skills", {})
    )

    db.add(new_player)
    db.commit()
    db.refresh(new_player)
    db.close()

    return {"msg": "Player created successfully!"}

@app.delete("/player/{username}")
def delete_player(username: str, token: str = Depends(oauth2_scheme)):
    db = SessionLocal()

    account = db.query(Account).filter_by(username=username).first()
    if not account:
        db.close()
        raise HTTPException(status_code=404, detail="Account not found.")

    player = db.query(Player).filter_by(account_id=account.id).first()
    if not player:
        db.close()
        raise HTTPException(status_code=404, detail="Player not found.")

    db.delete(player)
    db.commit()
    db.close()

    return {"msg": "Player deleted successfully."}

@app.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest):
    db = SessionLocal()
    account = db.query(Account).filter_by(email=request.email).first()
    db.close()
    if not account:
        raise HTTPException(status_code=404, detail="Email not found.")

    return {"msg": "Email found.", "username": account.username}

@app.post("/reset-password")
def reset_password(request: ResetPasswordRequest):
    db = SessionLocal()
    account = db.query(Account).filter_by(username=request.username).first()
    if not account:
        db.close()
        raise HTTPException(status_code=404, detail="Username not found.")

    hashed_password = pwd_context.hash(request.new_password)
    account.password_hash = hashed_password

    db.commit()
    db.close()

    return {"msg": "Password reset successfully."}
