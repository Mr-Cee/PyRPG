from player import Player
from items import create_item

# Create a test player
p = Player(name="TestHero", char_class="Warrior")

# Generate sample items
item1 = create_item("head", "Warrior", "Rare")
item2 = create_item("primary", "Warrior", "Uncommon")
item3 = create_item("amulet", "Warrior", "Legendary")

# Add to inventory
p.add_to_inventory(item1)
p.add_to_inventory(item2)
p.add_to_inventory(item3)

# View inventory
p.list_inventory()

# Equip items
p.equip_item(item1)
p.equip_item(item2)
p.equip_item(item3)

# View equipment
p.list_equipment()

# Unequip one item
p.unequip_item("primary")

# Final check
p.list_inventory()
p.list_equipment()