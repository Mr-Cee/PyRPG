import datetime
import json
import os
import requests
from items import create_item, EQUIP_SLOTS
from settings import SERVER_URL, CLIENT_VERSION  # or wherever your server runs

class Player:
    def __init__(self, name, char_class, level=1, experience=0, inventory=None, equipment=None, skills=None, username=None, role="player"):
        self.role = role
        self.username = username
        self.name = name
        self.char_class = char_class
        self.level = level
        self.experience = experience
        self.gold = 0
        self.inventory = inventory if inventory else []
        self.INVENTORY_SIZE = 49
        self.equipment = equipment if equipment else {
            "head": None,
            "shoulders": None,
            "chest": None,
            "gloves": None,
            "legs": None,
            "boots": None,
            "primary": None,
            "secondary": None,
            "amulet": None,
            "ring": None,
            "bracelet": None,
            "belt": None
        }
        self.skills = skills if skills else {}

        self.stats = {
            "Strength": 5,
            "Dexterity": 5,
            "Intelligence": 5,
            "Vitality": 5
        }

        self.chat_window = None

        self.last_heartbeat_time = 0
        self.heartbeat_interval = 30  # seconds

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

    def add_to_inventory(self, item):
        """Adds an item to the inventory if space is available."""
        if len(self.inventory) < self.INVENTORY_SIZE:
            self.inventory.append(item)
            self.chat_window.log(f"[Inventory] You've gained a {item['name']}", "System")
            return True
        else:
            self.chat_window.log("[Inventory] No space to add item!", "System")
            return False

    def remove_from_inventory(self, item):
        """Removes an item from the inventory."""
        if item in self.inventory:
            self.chat_window.log(f"[Inventory] Removing {item['name']} from inventory", "System")
            self.inventory.remove(item)
            return True
        else:
            self.chat_window.log(f"[Inventory] {item['name']} not found!", "Debug")
            return False

    def equip_item(self, item):
        """Equips an item from inventory to equipment slots."""
        subtype = item.get("subtype")
        item_type = item.get("type")

        if not subtype:
            self.chat_window.log(f"[Equip] Item missing subtype!", "Debug")
            return False

        # Verify that the slot exists
        if subtype not in self.equipment:
            self.chat_window.log(f"[Equip] No equipment slot for {subtype}.", "Debug")
            return False

        # Remove item from inventory
        if not self.remove_from_inventory(item):
            return False

        # If an item is already equipped, move it back to inventory
        if self.equipment[subtype]:
            self.add_to_inventory(self.equipment[subtype])

        # Equip new item
        self.equipment[subtype] = item
        self.chat_window.log(f"[Equip] Equipped {item['name']} to {subtype} slot.", "System")
        return True

    def unequip_item(self, slot):
        """Unequips an item from a given equipment slot back into inventory."""
        if slot not in self.equipment:
            self.chat_window.log(f"[Unequip] No such equipment slot: {slot}", "Debug")
            return False

        equipped_item = self.equipment.get(slot)
        if equipped_item:
            if self.add_to_inventory(equipped_item):
                self.equipment[slot] = None
                self.chat_window.log(f"[Unequip] Moved {equipped_item['name']} back to inventory.", "System")
                return True
            else:
                self.chat_window.log("[Unequip] Inventory full. Cannot unequip item.", "System")
                return False
        else:
            self.chat_window.log("[Unequip] No item equipped in that slot.", "Debug")
            return False

    def list_inventory(self):
        """Debug: List all items in the inventory."""
        print("\n-- Inventory --")
        for i, item in enumerate(self.inventory, 1):
            print(f"{i}: {item['name']} ({item['rarity']})")
        print("-- End Inventory --\n")

    def list_equipment(self):
        """Debug: List all equipped items."""
        print("\n-- Equipment --")
        for slot, item in self.equipment.items():
            if item:
                print(f"{slot.title()}: {item['name']} ({item['rarity']})")
            else:
                print(f"{slot.title()}: Empty")
        print("-- End Equipment --\n")

    def start_heartbeat(self, username):
        self._heartbeat_username = username
        self._heartbeat_running = True
        self._heartbeat_last_time = 0
        self._heartbeat_interval = 30  # seconds

    def stop_heartbeat(self):
        self._heartbeat_running = False

    def update_heartbeat(self, time_delta):
        if not self._heartbeat_running:
            return

        self._heartbeat_last_time += time_delta
        if self._heartbeat_last_time >= self._heartbeat_interval:
            self._heartbeat_last_time = 0
            try:
                requests.post(
                    f"{SERVER_URL}/heartbeat",
                    json={
                        "username": self._heartbeat_username,
                        "character_name": self.name,
                        "client_version": CLIENT_VERSION
                    },
                    timeout=2
                )
            except Exception as e:
                print(f"[Heartbeat Error] {e}")

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
            username=data["username"],
            role=data.get("role", "player")
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
                pass
                # print("[Server Sync] Player saved successfully.")
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
