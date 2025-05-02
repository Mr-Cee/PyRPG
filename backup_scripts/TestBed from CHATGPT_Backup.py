import pygame
import pygame_gui
import random

#from PIL.FontFile import WIDTH

pygame.init()

# ----- Window and UI Setup -----
WINDOW_SIZE = (1100, 700)
screen = pygame.display.set_mode(WINDOW_SIZE)
pygame.display.set_caption("Advanced Inventory + Equipment System")
clock = pygame.time.Clock()
manager = pygame_gui.UIManager(WINDOW_SIZE)
font = pygame.font.SysFont("Arial", 16)

# ----- Constants and Layout -----
SLOT_SIZE = 60
SLOT_MARGIN = 10
INVENTORY_SIZE = 20

# Multipliers
VITALITY_HP_MULT = 10
INTELLIGENCE_MP_MULT = 5
AGILITY_AVOID_MULT = 0.5

# Equipment slots
EQUIPMENT_SLOTS = [
    "head", "chest", "shoulders", "gloves", "belt", "legs", "boots",
    "primary", "secondary",
    "necklace", "ring", "bracelet"
]

# Slot-to-item-type map
EQUIPMENT_SLOT_TYPES = {
    "head": "Armor-Head",
    "chest": "Armor-Chest",
    "shoulders": "Armor-Shoulders",
    "gloves": "Armor-Gloves",
    "belt": "Armor-Belt",
    "legs": "Armor-Legs",
    "boots": "Armor-Boots",
    "primary": "Weapon",
    "secondary": ["Weapon", "Shield"],
    "necklace": "Jewelry-Necklace",
    "ring": "Jewelry-Ring",
    "bracelet": "Jewelry-Bracelet"
}

# ----- Classes -----
class Item:
    def __init__(self, name, item_type, stats):
        self.name = name
        self.type = item_type  # e.g. "Armor-Head", "Weapon", etc.
        self.stats = stats      # dict with base and special stats
        self.icon = self.load_icon()
        self.isEquipped = False


    def load_icon(self):
        icon_path = f"assets/icons/{self.type.lower().replace('-', '_')}.png"
        try:
            return pygame.image.load(icon_path).convert_alpha()
        except FileNotFoundError:
            return pygame.image.load("Assets/Icons/Missing_Texture.png")  # fallback if icon is missing

    def get_stat_text(self, compare_stats=None):
        if compare_stats is not None:
            lines = [f"(Equipped) <b>{self.name}</b>", f"Type: {self.type}"]
        else:
            lines = [f"<b>{self.name}</b>", f"Type: {self.type}"]


        for stat, value in self.stats.items():
            line = f"{stat.capitalize()}: {value}"
            if compare_stats and stat in compare_stats:
                if value > compare_stats[stat]:
                    line = f'<font color=#00FF00>{line}</font>'  # Green
                elif value < compare_stats[stat]:
                    line = f'<font color=#FF4040>{line}</font>'  # Red
            lines.append(line)
        return "<br>".join(lines)

    # def get_stat_text(self):
    #     base_stats = "<br>".join([f"{k.capitalize()}: {v}" for k, v in self.stats.items()])
    #     return f"<b>{self.name}</b><br>Type: {self.type}<br>{base_stats}"

class Player:
    def __init__(self):
        self.equipment = {slot: None for slot in EQUIPMENT_SLOTS}
        self.update_stats()

    def update_stats(self):
        self.stats = {
            "strength": 0,
            "agility": 0,
            "intelligence": 0,
            "vitality": 0,
            "armor": 0,
            "attack_power": 0,
            "block_chance": 0,
            "crit_chance": 0,
            "crit_damage": 0
        }

        for item in self.equipment.values():
            if item:
                for stat, val in item.stats.items():
                    self.stats[stat] = self.stats.get(stat, 0) + val

        # Derived stats
        self.hp = 100 + self.stats["vitality"] * VITALITY_HP_MULT
        self.mana = 50 + self.stats["intelligence"] * INTELLIGENCE_MP_MULT
        self.avoidance = self.stats["agility"] * AGILITY_AVOID_MULT

class Inventory:
    def __init__(self, size):
        self.maxSlots = 50
        self.slots = [None] * size
        self.rects = []
        self.scroll_offset = 0
        self.max_visible_rows = 2
        self.scroll_bar_rect = pygame.Rect(750, 500, 15, SLOT_SIZE * self.max_visible_rows + SLOT_MARGIN)

    def increase_size(self, amount):
        self.slots.extend([None] * amount)

    def sort_inventory(self):
        items = [item for item in self.slots if item is not None]
        self.slots = items + [None] * (len(self.slots) - len(items))

    def scroll(self, direction):
        max_rows = (len(self.slots) + 9) // 10
        self.scroll_offset = max(0, min(self.scroll_offset + direction, max_rows - self.max_visible_rows))

    def add_item(self, item):
        for i in range(len(self.slots)):
            if self.slots[i] is None:
                self.slots[i] = item
                return True
        return False

    def remove_item(self, index):
        if 0 <= index < len(self.slots):
            self.slots[index] = None

    def draw(self, surface):

        self.rects.clear()
        start_index = self.scroll_offset * 10
        end_index = min(start_index + self.max_visible_rows * 10, len(self.slots))
        for i in range(start_index, end_index):
            x = 50 + (i % 10) * (SLOT_SIZE + SLOT_MARGIN)
            y = 500 + ((i - start_index) // 10) * (SLOT_SIZE + SLOT_MARGIN)
            rect = pygame.Rect(x, y, SLOT_SIZE, SLOT_SIZE)
            self.rects.append(rect)
            pygame.draw.rect(surface, (100, 100, 100), rect, border_radius=4)
            if self.slots[i] and self.slots[i].icon:
                icon = pygame.transform.scale(self.slots[i].icon, (SLOT_SIZE - 12, SLOT_SIZE - 12))
                surface.blit(icon, (x + 6, y + 6))

    def get_slot_at_pos(self, pos):
        start_index = self.scroll_offset * 10
        end_index = min(start_index + self.max_visible_rows * 10, len(self.slots))

        for i in range(start_index, end_index):
            x = 50 + (i % 10) * (SLOT_SIZE + SLOT_MARGIN)
            y = 500 + ((i - start_index) // 10) * (SLOT_SIZE + SLOT_MARGIN)
            rect = pygame.Rect(x, y, SLOT_SIZE, SLOT_SIZE)
            if rect.collidepoint(pos):
                return i
        return None

class EquipmentUI:
    def __init__(self, x, y):
        self.slots = {slot: pygame.Rect(x + (i % 4) * 90, y + (i // 4) * 80, SLOT_SIZE, SLOT_SIZE)
                      for i, slot in enumerate(EQUIPMENT_SLOTS)}

    def draw(self, surface, player):
        for slot, rect in self.slots.items():
            pygame.draw.rect(surface, (60, 60, 60), rect, border_radius=4)
            label = font.render(slot, True, (200, 200, 200))
            surface.blit(label, (rect.x + SLOT_SIZE + 5, rect.y + 20))
            item = player.equipment[slot]
            if item:
                pygame.draw.rect(surface, (0, 100, 255), rect.inflate(-8, -8), border_radius=4)
                if item.icon:
                    icon = pygame.transform.scale(item.icon, (SLOT_SIZE - 12, SLOT_SIZE - 12))
                    surface.blit(icon, (rect.x + 6, rect.y + 6))
                else:
                    surface.blit(font.render(item.name[:3], True, (255, 255, 255)), (rect.x + 6, rect.y + 6))

    def get_slot_at_pos(self, pos):
        for slot, rect in self.slots.items():
            if rect.collidepoint(pos):
                return slot
        return None

# ---- GUI Elements ----
undo_button = pygame_gui.elements.UIButton(pygame.Rect((100, 650), (80, 40)), "Undo", manager)
undo_button.hide()
last_deleted_item = None
trash_icon = pygame_gui.elements.UIImage(pygame.Rect((50, 650), (40, 40)), pygame.image.load("assets/icons/trashcan.png"), manager=manager)
delete_confirmation_dialog = None
delete_candidate = None
pickup_button = pygame_gui.elements.UIButton(pygame.Rect((50, 50), (150, 40)), "Pick Up Item", manager)
hover_box = pygame_gui.elements.UITextBox("", pygame.Rect((850, 50), (230, 325)), manager)
hover_box.hide()
comparison_box = pygame_gui.elements.UITextBox("", pygame.Rect((500, 50), (250, 325)), manager)
comparison_box.hide()
stats_box = pygame_gui.elements.UITextBox("", pygame.Rect((850, 500), (230, 180)), manager)
sort_button = pygame_gui.elements.UIButton(pygame.Rect((220, 50), (120, 40)), "Sort Inventory", manager)
tooltip = pygame_gui.elements.UITextBox("", pygame.Rect((850, 50), (200, 300)), manager)
tooltip.hide()
# stats_box = pygame_gui.elements.UITextBox("", pygame.Rect((850, 200), (200, 180)), manager)

# ---- Game Logic ----
player = Player()
inventory = Inventory(INVENTORY_SIZE)
equipment_ui = EquipmentUI(50, 100)

STAT_CATEGORIES = ["strength", "agility", "intelligence", "vitality", "armor", "attack_power", "block_chance", "crit_chance", "crit_damage"]

ITEM_POOL = [
    ("Iron Helm", "Armor-Head"),
    ("Basic Helm", "Armor-Head"),
    ("Steel Chest", "Armor-Chest"),
    ("Leather Gloves", "Armor-Gloves"),
    ("Sword", "Weapon"),
    ("Tower Shield", "Shield"),
    ("Necklace of Insight", "Jewelry-Necklace"),
    ("Ring of Speed", "Jewelry-Ring"),
    ("Bracelet of Might", "Jewelry-Bracelet")
]

def generate_random_item():
    name, itype = random.choice(ITEM_POOL)
    stats = {stat: random.randint(0, 5) for stat in STAT_CATEGORIES}
    return Item(name, itype, stats)

def update_stat_display():
    p = player
    stat_text = f"<b>Player Stats</b><br>HP: {p.hp}<br>MP: {p.mana}<br>AVD: {p.avoidance:.1f}<br>"
    for stat, val in p.stats.items():
        stat_text += f"{stat.capitalize()}: {val}<br>"
    stats_box.set_text(stat_text)

update_stat_display()

# ---- Drag/Drop State ----
dragging_item = None
dragging_index = None
dragging_from_equipment = None
confirm_deletion = False

# ---- Main Game Loop ----
running = True
while running:
    dt = clock.tick(60) / 1000
    mouse_pos = pygame.mouse.get_pos()

    # Tooltip hover
    # Tooltip hover + comparison logic
    idx = inventory.get_slot_at_pos(mouse_pos)
    equipment_slot = equipment_ui.get_slot_at_pos(mouse_pos)
    hovered_item = None

    hover_box.hide()
    comparison_box.hide()

    if idx is not None and inventory.slots[idx]:
        hovered_item = inventory.slots[idx]
        hover_box.set_text(hovered_item.get_stat_text())
        hover_box.show()

        # Show comparison if an item of the same type is equipped
        for slot, type_req in EQUIPMENT_SLOT_TYPES.items():
            if (isinstance(type_req, list) and hovered_item.type in type_req) or (hovered_item.type == type_req):
                equipped_item = player.equipment.get(slot)
                if equipped_item:
                    #print("HERE")
                    comparison_box.set_text(equipped_item.get_stat_text(hovered_item.stats))
                    comparison_box.show()
                break

    # When hovering over an equipped item, show stat box
    elif equipment_slot and player.equipment[equipment_slot]:
        hovered_item = player.equipment[equipment_slot]
        comparison_box.set_text(hovered_item.get_stat_text())
        comparison_box.show()


    for event in pygame.event.get():


        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_i:
                if len(inventory.slots) <= inventory.maxSlots - 10:
                    inventory.increase_size(10)
                    print(f"KeyEvent {len(inventory.slots)}")
        if event.type == pygame.MOUSEWHEEL:
            inventory.scroll(-event.y)

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == pickup_button:
                item = generate_random_item()
                if not inventory.add_item(item):
                    print("Full Inventory")
            elif event.ui_element == sort_button:
                inventory.sort_inventory()
            elif event.ui_element == undo_button and last_deleted_item:
                item, idx, from_eq = last_deleted_item
                if idx is not None and inventory.slots[idx] is None:
                    inventory.slots[idx] = item
                elif from_eq is not None and player.equipment[from_eq] is None:
                    player.equipment[from_eq] = item
                    player.update_stats()
                    update_stat_display()
                last_deleted_item = None
                undo_button.hide()

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                idx = inventory.get_slot_at_pos(event.pos)
                equipment_slot = equipment_ui.get_slot_at_pos(event.pos)
                if idx is not None and inventory.slots[idx]:
                    dragging_item = inventory.slots[idx]
                    dragging_index = idx
                    inventory.slots[idx] = None
                elif equipment_slot and player.equipment[equipment_slot]:
                    dragging_item = player.equipment[equipment_slot]
                    dragging_from_equipment = equipment_slot
                    player.equipment[equipment_slot] = None
                    player.update_stats()
                    update_stat_display()

            # Right Click to Equip items
            elif event.button == 3:
                idx = inventory.get_slot_at_pos(event.pos)
                if idx is not None and inventory.slots[idx]:
                    item = inventory.slots[idx]
                    for slot, type_req in EQUIPMENT_SLOT_TYPES.items():
                        if (isinstance(type_req, list) and item.type in type_req) or (item.type == type_req):
                            if player.equipment[slot]:
                                inventory.slots[idx] = player.equipment[slot]

                            else:
                                inventory.slots[idx] = None
                            player.equipment[slot] = item

                            player.update_stats()
                            update_stat_display()
                            break


        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if dragging_item:
                idx = inventory.get_slot_at_pos(event.pos)
                equipment_slot = equipment_ui.get_slot_at_pos(event.pos)
                item_placed = False

                # --- Dropped onto inventory slot ---
                if idx is not None:
                    if inventory.slots[idx] is None:
                        inventory.slots[idx] = dragging_item
                        item_placed = True
                    else:
                        # Swap if from inventory
                        if dragging_index is not None:
                            inventory.slots[dragging_index] = inventory.slots[idx]
                            inventory.slots[idx] = dragging_item
                            item_placed = True
                        else:
                            # Equip-to-inventory swap (fallback)
                            if inventory.add_item(inventory.slots[idx]):
                                inventory.slots[idx] = dragging_item

                                item_placed = True

                # --- Dropped onto equipment slot ---
                elif equipment_slot is not None:
                    expected_types = EQUIPMENT_SLOT_TYPES[equipment_slot]
                    is_compatible = (
                        dragging_item.type in expected_types
                        if isinstance(expected_types, list)
                        else dragging_item.type == expected_types
                    )

                    if is_compatible:
                        if player.equipment[equipment_slot]:
                            inventory.add_item(player.equipment[equipment_slot])
                        player.equipment[equipment_slot] = dragging_item

                        player.update_stats()
                        update_stat_display()
                        item_placed = True

                # Logic for dragging item onto the trash can and getting a popup for deletion
                elif trash_icon.rect.collidepoint(mouse_pos):
                    delete_candidate = (dragging_item, dragging_index, dragging_from_equipment)
                    delete_confirmation_dialog = pygame_gui.windows.UIConfirmationDialog(
                        rect=pygame.Rect((350, 250), (400, 200)),
                        manager=manager,
                        window_title='Delete Item?',
                        action_long_desc=f"Are you sure you want to delete {dragging_item.name}?",
                        action_short_name='Delete',
                        blocking=True
                    )

                # --- If nothing was placed, return it ---
                if not item_placed:
                    if dragging_index is not None:
                        if inventory.slots[dragging_index] is None:
                            inventory.slots[dragging_index] = dragging_item
                        else:
                            inventory.add_item(dragging_item)
                    elif dragging_from_equipment is not None:
                        if player.equipment[dragging_from_equipment] is None:
                            player.equipment[dragging_from_equipment] = dragging_item

                        else:
                            inventory.add_item(dragging_item)
                    player.update_stats()
                    update_stat_display()

                # Reset drag state
                dragging_item = None
                dragging_index = None
                dragging_from_equipment = None

        if event.type == pygame_gui.UI_CONFIRMATION_DIALOG_CONFIRMED and event.ui_element == delete_confirmation_dialog:
            if delete_candidate:
                item, idx, from_eq = delete_candidate
                if idx is not None:
                    inventory.slots[idx] = None
                elif from_eq is not None:
                    player.equipment[from_eq] = None
                    player.update_stats()
                    update_stat_display()
                last_deleted_item = (item, idx, from_eq)
                undo_button.show()
                delete_candidate = None

        if event.type == pygame_gui.UI_CONFIRMATION_DIALOG_CONFIRMED and event.ui_element == delete_confirmation_dialog:
            delete_candidate = None



        manager.process_events(event)




    manager.update(dt)
    screen.fill((20, 20, 20))
    inventory.draw(screen)
    equipment_ui.draw(screen, player)

    if dragging_item:
        mx, my = pygame.mouse.get_pos()
        # pygame.draw.rect(screen, (255, 200, 0), (mx, my, SLOT_SIZE, SLOT_SIZE), border_radius=4)
        # label = font.render(dragging_item.name[:3], True, (0, 0, 0))
        #screen.blit(dragging_item.icon, (mx + 6, my + 6))
        dragging_item.icon = pygame.transform.scale(dragging_item.icon, (SLOT_SIZE - 12, SLOT_SIZE - 12))
        screen.blit(dragging_item.icon, (mx+ 6, my + 6, SLOT_SIZE, SLOT_SIZE))

    # Draw scroll bar
    total_rows = (len(inventory.slots) + 9) // 10
    if total_rows > inventory.max_visible_rows:
        bar_height = inventory.scroll_bar_rect.height
        handle_height = max(20, bar_height * inventory.max_visible_rows // total_rows)
        handle_y = inventory.scroll_bar_rect.y + (bar_height - handle_height) * inventory.scroll_offset // (total_rows - inventory.max_visible_rows)
        handle_rect = pygame.Rect(inventory.scroll_bar_rect.x, handle_y, inventory.scroll_bar_rect.width, handle_height)
        pygame.draw.rect(screen, (120, 120, 120), inventory.scroll_bar_rect)
        pygame.draw.rect(screen, (200, 200, 200), handle_rect)

    manager.draw_ui(screen)
    pygame.display.update()

pygame.quit()
