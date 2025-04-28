import datetime
import json
import os
import requests

SERVER_URL = "http://localhost:8000"  # or wherever your server runs

class Player:
    def __init__(self, name, char_class, level=1, experience=0, inventory=None, equipment=None, skills=None, username=None):
        self.username = username
        self.name = name
        self.char_class = char_class
        self.level = level
        self.experience = experience
        self.gold = 0
        self.inventory = inventory if inventory else []
        self.equipment = equipment if equipment else {
            "head": None,
            "chest": None,
            "legs": None,
            "boots": None,
            "weapon": None
        }
        self.skills = skills if skills else {}

        self.stats = {
            "Strength": 5,
            "Dexterity": 5,
            "Intelligence": 5,
            "Vitality": 5
        }

        self.chat_window = None

        self.last_logout_time = None  # Track when they logged out
        self.pending_idle_rewards = None  # Store calculated rewards when logging back in

    def gain_experience(self, amount):
        self.experience += amount
        if self.experience >= self.get_exp_to_next_level():
            self.level_up()

    def get_exp_to_next_level(self):
        return self.level * 100

    def level_up(self):
        self.level += 1
        self.experience = 0
        print(f"{self.name} leveled up to {self.level}!")

    def save(self):
        os.makedirs('Save_Data/Characters', exist_ok=True)
        save_path = f"Save_Data/Characters/{self.name}.json"
        with open(save_path, 'w') as f:
            json.dump(self.to_dict(), f)

    def to_dict(self):
        return {
            "name": self.name,
            "char_class": self.char_class,
            "level": self.level,
            "experience": self.experience,
            "stats": self.stats,
            "inventory": self.inventory,
            "equipment": self.equipment,
            "last_logout_time": self.last_logout_time.isoformat() if self.last_logout_time else None
        }

    @staticmethod
    def load(name):
        path = f"Save_Data/Characters/{name}.json"
        if not os.path.exists(path):
            return None
        with open(path, 'r') as f:
            data = json.load(f)
            player = Player(
                name=data["name"],
                char_class=data["char_class"],
                level=data.get("level", 1),
                experience=data.get("experience", 0),
                inventory=data.get("inventory", []),
                equipment=data.get("equipment", {})
            )
            player.stats = data.get("stats", player.stats)
            if data.get("last_logout_time"):
                player.last_logout_time = datetime.datetime.fromisoformat(data["last_logout_time"])
            return player

    @classmethod
    def from_server_data(cls, data):
        player = cls(
            name=data["name"],
            char_class=data["char_class"],
            level=data["level"],
            experience=data["experience"],
            inventory=data["inventory"],
            equipment=data["equipment"],
            skills=data["skills"],
            username=data["username"]
        )
        if data.get("last_logout_time"):
            player.last_logout_time = datetime.datetime.fromisoformat(data["last_logout_time"])

        player.gold = data.get("gold", 0)

        return player

    def save_to_server(self, auth_token):
        try:
            headers = {
                "Authorization": f"Bearer {auth_token}"
            }
            payload = {
                "username": self.username,  # you must have self.username stored!
                "name": self.name,
                "level": self.level,
                "experience": self.experience,
                "gold": getattr(self, 'gold', 0),  # default to 0 if no gold yet
                "last_logout_time": self.last_logout_time.isoformat() if self.last_logout_time else datetime.datetime.utcnow().isoformat()
            }
            response = requests.post(f"{SERVER_URL}/update_player", json=payload, headers=headers)
            if response.status_code == 200:
                print("[Server Sync] Player saved successfully.")
            else:
                print(f"[Server Sync] Failed to save player. {response.status_code}: {response.text}")
        except Exception as e:
            print(f"[Server Sync] Error saving player: {e}")

    def calculate_idle_rewards(self):
        if not self.last_logout_time:
            return

        now = datetime.datetime.now(datetime.UTC)
        elapsed = now - self.last_logout_time

        max_offline_seconds = 4 * 60 * 60  # 4 hours max
        offline_seconds = min(elapsed.total_seconds(), max_offline_seconds)

        reward_xp = int(offline_seconds // 10)  # 1 XP per 10 seconds
        reward_gold = int(offline_seconds // 5)  # 1 gold per 5 seconds

        if reward_xp > 0 or reward_gold > 0:
            self.pending_idle_rewards = {
                "xp": reward_xp,
                "gold": reward_gold
            }
