GAME_WIDTH = 1280
GAME_HEIGHT = 720

CLIENT_VERSION = "v0.0.5"

PUBLIC_IP = "75.119.187.81"

# ⚙️ Server Settings (FastAPI)
SERVER_HOST = f"{PUBLIC_IP}"  # change to your server's LAN IP
SERVER_PORT = 8000
SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"

rarity_colors = {
    "Common": "#c0c0c0", #Gray
    "Uncommon": "#1eff00", #Green
    "Rare": "#0070dd", #Blue
    "Epic": "#a335ee", #Purple
    "Legendary": "#ff8000", #Orange
    "Mythical": "#e60000" #Red
}

