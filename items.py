import random

RARITY_TIERS = {
    "Common": 60,
    "Uncommon": 25,
    "Rare": 10,
    "Legendary": 3,
    "Mythical": 2
}

EQUIP_SLOTS = {
    "armor": ["head", "shoulders", "chest", "gloves", "legs", "boots"],
    "weapon": ["primary", "secondary"],
    "accessory": ["amulet", "ring", "bracelet", "belt"]
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

# Base stat ranges per rarity
RARITY_MULTIPLIERS = {
    "Common": 1.0,
    "Uncommon": 1.25,
    "Rare": 1.5,
    "Legendary": 2.0,
    "Mythical": 3.0
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


def create_item(slot_type, char_class="Warrior", rarity=None, slot=None):
    rarity = pick_rarity() if rarity is None else rarity
    multiplier = RARITY_MULTIPLIERS[rarity]
    main_stat = PLAYER_CLASSES.get(char_class, "Strength")

    item = {
        "name": f"{rarity} {slot_type.title()} Item",
        "type": get_type_from_slot(slot_type),
        "subtype": slot_type,
        "rarity": rarity,
        "stats": {},
        "slot": slot,  # ✅ Add this
        "icon": f"Assets/Items/{slot_type}.png"  # ✅ Simple default icon path
    }

    # Shared stat distribution logic
    item["stats"][main_stat] = int(5 * multiplier)
    item["stats"]["Vitality"] = int(4 * multiplier)

    if slot_type in EQUIP_SLOTS["armor"]:
        item["stats"]["Armor"] = int(6 * multiplier)

    elif slot_type == "primary":
        item["stats"]["Weapon Damage"] = int(10 * multiplier)

    elif slot_type == "secondary":
        item["stats"]["Weapon Damage"] = int(5 * multiplier)
        item["stats"]["Block"] = round(5 * multiplier, 1) if char_class == "Warrior" else round(3 * multiplier, 1)
        item["stats"]["Dodge"] = round(5 * multiplier, 1) if char_class == "Rogue" else round(2 * multiplier, 1)

    elif slot_type in EQUIP_SLOTS["accessory"]:
        item["stats"]["Critical Chance"] = round(3 * multiplier, 1)
        item["stats"]["Critical Damage"] = round(7 * multiplier, 1)

    return item


def get_type_from_slot(slot):
    for k, v in EQUIP_SLOTS.items():
        if slot in v:
            return k
    return "misc"