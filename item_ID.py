# item_ID.py

WOODCUTTING_ITEMS = {
    1: {"name": "Oak Log", "level": 1, "rarity": "Common"},
    2: {"name": "Spruce Log", "level": 2, "rarity": "Common"},
    3: {"name": "Pine Log", "level": 3, "rarity": "Uncommon"},
    4: {"name": "Birch Log", "level": 5, "rarity": "Uncommon"},
    5: {"name": "Maple Log", "level": 7, "rarity": "Rare"},
    6: {"name": "Ash Log", "level": 10, "rarity": "Rare"},
    7: {"name": "Willow Log", "level": 13, "rarity": "Rare"},
    8: {"name": "Cedar Log", "level": 16, "rarity": "Legendary"},
    9: {"name": "Redwood Log", "level": 20, "rarity": "Legendary"},
    10: {"name": "Ancient Bark", "level": 25, "rarity": "Mythical"}
}

MINING_ITEMS = {
    100: {"name": "Copper Chunk", "level": 1, "rarity": "Common"},
    101: {"name": "Tin Chunk", "level": 2, "rarity": "Common"},
    102: {"name": "Iron Ore", "level": 4, "rarity": "Uncommon"},
    103: {"name": "Silver Ore", "level": 6, "rarity": "Uncommon"},
    104: {"name": "Gold Nugget", "level": 9, "rarity": "Rare"},
    105: {"name": "Platinum Ore", "level": 12, "rarity": "Rare"},
    106: {"name": "Mithril Fragment", "level": 15, "rarity": "Legendary"},
    107: {"name": "Adamantite Shard", "level": 18, "rarity": "Legendary"},
    108: {"name": "Runestone", "level": 22, "rarity": "Mythical"},
    109: {"name": "Gem Cluster", "level": 25, "rarity": "Mythical"}
}

FARMING_ITEMS = {
    200: {"name": "Cotton Bundle", "level": 1, "rarity": "Common"},
    201: {"name": "Jute Bundle", "level": 2, "rarity": "Common"},
    202: {"name": "Flax Bundle", "level": 3, "rarity": "Uncommon"},
    203: {"name": "Wool Bundle", "level": 5, "rarity": "Uncommon"},
    204: {"name": "Silk Cocoon", "level": 8, "rarity": "Rare"},
    205: {"name": "Raw Wheat", "level": 10, "rarity": "Rare"},
    206: {"name": "Barley Husk", "level": 13, "rarity": "Rare"},
    207: {"name": "Oat Straw", "level": 16, "rarity": "Legendary"},
    208: {"name": "Herb Sprig", "level": 20, "rarity": "Legendary"},
    209: {"name": "Root Vegetable", "level": 25, "rarity": "Mythical"}
}

SCAVENGING_ITEMS = {
    300: {"name": "Scrap Leather", "level": 1, "rarity": "Common"},
    301: {"name": "Torn Hide", "level": 2, "rarity": "Common"},
    302: {"name": "Worn Fabric", "level": 3, "rarity": "Uncommon"},
    303: {"name": "Broken Needle", "level": 5, "rarity": "Uncommon"},
    304: {"name": "Rusty Gear", "level": 8, "rarity": "Rare"},
    305: {"name": "Cracked Bone", "level": 10, "rarity": "Rare"},
    306: {"name": "Cloth Strap", "level": 13, "rarity": "Rare"},
    307: {"name": "Grease Stain", "level": 16, "rarity": "Legendary"},
    308: {"name": "Rat Tail", "level": 20, "rarity": "Legendary"},
    309: {"name": "Lost Trinket", "level": 25, "rarity": "Mythical"}
}

ALL_ITEMS = {
    **WOODCUTTING_ITEMS,
    **MINING_ITEMS,
    **FARMING_ITEMS,
    **SCAVENGING_ITEMS
}

def get_item_name(item_id):
    return ALL_ITEMS.get(item_id, {}).get("name", f"Unknown Item #{item_id}")

def get_item_level(item_id):
    return ALL_ITEMS.get(item_id, {}).get("level", 0)

def get_item_rarity(item_id):
    return ALL_ITEMS.get(item_id, {}).get("rarity", "Unknown")
