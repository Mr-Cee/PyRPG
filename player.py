# player.py

class Player:
    def __init__(self, name, char_class, level=1, experience=0):
        self.name = name
        self.char_class = char_class
        self.level = level
        self.experience = experience

        self.stats = {
            "Strength": 5,
            "Dexterity": 5,
            "Intelligence": 5,
            "Vitality": 5
        }

        self.inventory = []
        self.equipment = {
            "head": None,
            "chest": None,
            "legs": None,
            "boots": None,
            "weapon": None
        }

        self.chat_window = None  # <<< We'll attach your existing chat system here!

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
        import os, json
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
            "equipment": self.equipment
            # (You could add more stuff later here!)
        }

    @staticmethod
    def load(name):
        import os, json
        path = f"Save_Data/Characters/{name}.json"
        if not os.path.exists(path):
            return None
        with open(path, 'r') as f:
            data = json.load(f)
            player = Player(
                name=data["name"],
                char_class=data["char_class"],
                level=data.get("level", 1),
                experience=data.get("experience", 0)
            )
            player.stats = data.get("stats", player.stats)
            player.inventory = data.get("inventory", [])
            player.equipment = data.get("equipment", player.equipment)
            return player