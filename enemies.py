ENEMY_TIERS = [
    {"min_level": 1, "name": "Slime", "base_hp": 25, "base_dmg": 2, "base_speed": 0.5, "base_xp": 10, "base_copper": 5},
    {"min_level": 10, "name": "Goblin", "base_hp": 40, "base_dmg": 10, "base_speed": 0.7, "base_xp": 20, "base_copper": 50},
    {"min_level": 20, "name": "Orc", "base_hp": 70, "base_dmg": 18, "base_speed": 0.9, "base_xp": 35, "base_copper": 100},
    {"min_level": 30, "name": "Dark Knight", "base_hp": 100, "base_dmg": 28, "base_speed": 1.1, "base_xp": 60, "base_copper": 200},
    {"min_level": 40, "name": "Dragonling", "base_hp": 140, "base_dmg": 35, "base_speed": 1.3, "base_xp": 90, "base_copper": 300},
]

# List of fun prefixes
NAME_PREFIXES = [
    "Savage", "Vile", "Corrupted", "Twisted", "Lurking",
    "Furious", "Enraged", "Brutal", "Dark", "Wild", "Grimy", "Malformed"
]

# List of elite prefixes (special and rare)
ELITE_PREFIXES = ["Dread", "Alpha", "Ancient", "Frenzied", "Mythic"]

ELITE_AURA_COLORS = {
    "Dread": "#FF3333",    # Intense red
    "Alpha": "#3399FF",    # Bright blue
    "Ancient": "#9933FF",  # Purple
    "Frenzied": "#FF9900", # Orange
    "Mythic": "#FFD700",   # Gold
}