import random
from settings import *



EQUIP_SLOTS = {
    "armor": ["head", "shoulders", "chest", "gloves", "legs", "boots"],
    "weapon": ["primary", "secondary"],
    "accessory": ["amulet", "ring", "bracelet", "belt"]
}

WEAPON_TYPES = {
    "Sword":  {"slots": 1, "block": False, "speed_secondary_penalty": True,  "base_damage": 12, "base_speed": 1.0},
    "Dagger": {"slots": 1, "block": False, "speed_secondary_penalty": True,  "base_damage": 10, "base_speed": 1.2},
    "Staff":  {"slots": 2, "block": False, "speed_secondary_penalty": False, "base_damage": 18, "base_speed": 0.8},
    "Bow":    {"slots": 2, "block": False, "speed_secondary_penalty": False, "base_damage": 20, "base_speed": 0.7},
    "Shield": {"slots": 1, "block": True,  "speed_secondary_penalty": False, "base_block": 15},
    "Focus":  {"slots": 1, "block": False, "speed_secondary_penalty": False, "base_damage": 8,  "base_speed": 1.1},
}

STAT_TYPES = [
    "Strength", "Intelligence", "Agility", "Vitality",
    "Critical Chance", "Critical Damage", "Block", "Armor", "Dodge"
]

PLAYER_CLASSES = {
    "Warrior": "Strength",
    "Mage": "Intelligence",
    "Rogue": "Agility"
}

def pick_rarity(rng=None, rarity_override=None):
    if rarity_override:
        return rarity_override
    rng = rng or random.random()
    threshold = 0
    for rarity, chance in RARITY_TIERS.items():
        threshold += chance / 100
        if rng < threshold:
            return rarity
    return "Common"  # fallback


def create_item(slot_type, char_class="Warrior", rarity=None, slot=None, weapon_type=None, item_level=1):
    rarity = pick_rarity() if rarity is None else rarity
    multiplier = RARITY_MULTIPLIERS[rarity]
    main_stat = PLAYER_CLASSES.get(char_class, "Strength")


    # Item level scaling factor (example formula: linear scale)
    level_scale = 1 + (item_level - 1) * 0.2  # Each level adds 20% more power

    if slot_type in ("primary", "secondary") and weapon_type:
        item_name = f"{rarity} {weapon_type} | (Lv{item_level})"
    else:
        item_name = f"{rarity} {slot_type.title()} | (Lv{item_level})"

    item = {
        "name": item_name,
        "type": get_type_from_slot(slot_type),
        "subtype": slot_type,
        "rarity": rarity,
        "level": item_level,
        "stats": {},
        "slot": slot,
        "icon": f"Assets/Items/{weapon_type.lower()}.png" if slot_type in ("primary", "secondary") and weapon_type else f"Assets/Items/{slot_type}.png"
    }
    # Shared stat distribution logic
    item["stats"][main_stat] = int(5 * multiplier * level_scale)
    item["stats"]["Vitality"] = int(4 * multiplier * level_scale)

    if slot_type in EQUIP_SLOTS["armor"]:
        item["stats"]["Armor"] = int(6 * multiplier * level_scale)

    elif slot_type in ("primary", "secondary") and weapon_type in WEAPON_TYPES:
        item["weapon_type"] = weapon_type
        wt = WEAPON_TYPES[weapon_type]

        if wt["block"]:
            item["stats"]["Block"] = int(wt["base_block"] * multiplier * level_scale)
        else:
            base = int(wt["base_damage"] * multiplier * level_scale)
            min_damage = max(1, int(base * 0.85))  # 85% of base
            max_damage = int(base * 1.15)  # 115% of base
            item["stats"]["Min Damage"] = min_damage
            item["stats"]["Max Damage"] = max_damage
            # item["stats"]["Weapon Damage"] = int(wt["base_damage"] * multiplier * level_scale)

            if slot_type == "secondary":
                # Secondary hand penalty
                penalty = -0.10 if char_class == "Rogue" else -0.05
                speed = wt["base_speed"] + penalty
            else:
                speed = wt["base_speed"]

            item["stats"]["Attack Speed"] = round(speed, 2)

    elif slot_type == "primary" and weapon_type is None:
        item["stats"]["Weapon Damage"] = int(10 * multiplier * level_scale)
        item["stats"]["Attack Speed"] = round(1.0 - (0.05 * multiplier), 2)

    elif slot_type == "secondary" and weapon_type is None:
        item["stats"]["Weapon Damage"] = int(5 * multiplier * level_scale)
        item["stats"]["Block"] = round((5 if char_class == "Warrior" else 3) * multiplier * level_scale, 1)
        item["stats"]["Dodge"] = round((5 if char_class == "Rogue" else 2) * multiplier * level_scale, 1)
        item["stats"]["Attack Speed"] = round(1.0 - (0.03 * multiplier), 2)

    elif slot_type in EQUIP_SLOTS["accessory"]:
        item["stats"]["Critical Chance"] = round(3 * multiplier * level_scale, 1)
        item["stats"]["Critical Damage"] = round(7 * multiplier * level_scale, 1)

    return item


def get_type_from_slot(slot):
    for k, v in EQUIP_SLOTS.items():
        if slot in v:
            return k
    return "misc"