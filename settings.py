GAME_WIDTH = 1280
GAME_HEIGHT = 720

CLIENT_VERSION = "v0.0.6"

PUBLIC_IP = "75.119.187.81"

# ⚙️ Server Settings (FastAPI)
SERVER_HOST = f"{PUBLIC_IP}"  # change to your server's LAN IP
SERVER_PORT = 8000
SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

RARITY_TIERS = {
    "Common": 65,
    "Uncommon": 25,
    "Rare": 10,
    "Epic": 5,
    "Legendary": 3,
    "Mythical": 2
}

# Base stat ranges per rarity
RARITY_MULTIPLIERS = {
    "Common": 1.0,
    "Uncommon": 1.25,
    "Rare": 1.5,
    "Epic": 2.0,
    "Legendary": 3.0,
    "Mythical": 5.0
}

rarity_colors = {
    "Common": "#c0c0c0", #Gray
    "Uncommon": "#1eff00", #Green
    "Rare": "#0070dd", #Blue
    "Epic": "#a335ee", #Purple
    "Legendary": "#ff8000", #Orange
    "Mythical": "#e60000" #Red
}

