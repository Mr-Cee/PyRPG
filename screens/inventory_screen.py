import math
import time
import pygame.gfxdraw
import pygame
import pygame_gui
from pygame import Rect
import requests

from chat_system import ChatWindow
from settings import SERVER_URL, rarity_colors
from screen_manager import BaseScreen
from screen_registry import ScreenRegistry

#Load and scale the background image once
INVENTORY_BG_IMAGE = pygame.image.load("Assets/GUI/Inventory/inner_carving.png").convert_alpha()
INVENTORY_BG_IMAGE = pygame.transform.scale(INVENTORY_BG_IMAGE, (302, 309))  # Match grid area
ROW_IMAGE = pygame.image.load("Assets/GUI/Inventory/row_slot.png").convert_alpha()


CHAR_FRAME_IMAGE = pygame.image.load("Assets/GUI/Inventory/character_sheet_frame.png").convert_alpha()
CHAR_FRAME_IMAGE = pygame.transform.scale(CHAR_FRAME_IMAGE, (327, 444))
CHAR_VERTICAL_SLOTS = pygame.image.load("Assets/GUI/Inventory/Character_Sheet_Vertical_Slots.png").convert_alpha()
CHAR_VERTICAL_SLOTS = pygame.transform.scale(CHAR_VERTICAL_SLOTS, (52, 292))



class InventoryScreen(BaseScreen):
    def __init__(self, manager, screen_manager):
        super().__init__(manager, screen_manager)
        self.player = screen_manager.player
        self.dragging_item = None
        self.dragging_index = None
        self.drag_icon = None
        self.hovered_slot_index = None
        self.tooltip = None

        self.inventory_slots = []
        self.inventory_rows = []
        self.container_width = 314  # +8 pixels for right edge breathing room
        self.grid_origin_x = 10
        self.grid_origin_y = 60
        self.row_width = 305
        self.row_height = 52
        self.columns = 6
        self.slot_size = 46
        self.slot_padding = 4
        self.num_rows = 6  # Can later expand dynamically
        # self.container_height = self.num_rows * 52
        self.container_height = (self.num_rows * 56) + 10

    def setup(self):
        # Back button
        self.back_button = pygame_gui.elements.UIButton(
            relative_rect=Rect((10, 10), (100, 30)),
            text="Back",
            manager=self.manager
        )

        # Title label
        self.title_label = pygame_gui.elements.UILabel(
            relative_rect=Rect((130, 10), (300, 30)),
            text="Inventory (WIP)",
            manager=self.manager
        )

        self.player.chat_window = ChatWindow(self.manager, self.player, self.screen_manager, container=None, inventory_screen=self)
        self.player.chat_window.panel.set_relative_position((10, 480))
        self.player.chat_window.panel.set_dimensions((400, 220))


        self.setup_character_sheet()
        self.setup_inventory()

    def setup_inventory(self):
        # Setting up Grid
        # Outer inventory container (frame)
        self.inventory_container = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect((self.grid_origin_x, self.grid_origin_y),
                                      (self.container_width, self.container_height)),
            manager=self.manager
        )

        self.bg_image = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect((0, 0), (self.container_width, self.container_height)),
            image_surface=pygame.transform.scale(INVENTORY_BG_IMAGE, (self.container_width, self.container_height)),
            manager=self.manager,
            container=self.inventory_container
        )

        for row_index in range(self.num_rows):
            row_y = row_index * (self.row_height + 4)

            row_panel = pygame_gui.elements.UIPanel(
                relative_rect=pygame.Rect((0, row_y), (308, 60)),
                manager=self.manager,
                container=self.inventory_container
            )
            self.inventory_rows.append(row_panel)

            bg_image = pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect((0, 0), (302, 52)),
                image_surface=ROW_IMAGE,
                manager=self.manager,
                container=row_panel
            )

            for col_index in range(self.columns):
                slot_x = 3 + col_index * (46 + 4)  # Start at 3px in, match spacing
                slot_panel = pygame_gui.elements.UIPanel(
                    relative_rect=pygame.Rect((slot_x, 3), (46, 46)),
                    manager=self.manager,
                    container=row_panel
                )
                self.inventory_slots.append(slot_panel)

        self.slot_icons = []

        # Fetch inventory data from backend
        player_name = self.screen_manager.player.name
        try:
            response = requests.get(f"{SERVER_URL}/inventory/{player_name}", timeout=5)
            response.raise_for_status()
            inventory_data = response.json()
            self.inventory_data = inventory_data
        except Exception as e:
            print(f"[Inventory] Failed to load inventory: {e}")
            inventory_data = []  # fallback to empty

        self.render_inventory_icons()

        self.hover_tooltip_box = pygame_gui.elements.UITextBox(
            html_text="",
            relative_rect=pygame.Rect((330, 60), (200, 200)),  # Adjust position/size as needed
            manager=self.manager
        )
        self.hover_tooltip_box.hide()

        self.coin_label = pygame_gui.elements.UILabel(
            relative_rect=Rect((self.grid_origin_x, self.grid_origin_y + self.container_height + 5), (180, 30)),
            text=f"Coins: {self.player.format_coins()}",
            manager=self.manager
        )

        self.player.register_coin_update_callback(self.refresh_coin_display)

    def setup_character_sheet(self):
        self.equip_slot_size = 44
        self.equip_slot_padding = 0
        self.equip_slot_origin_y = (444 - (6 * 44 + 5 * 4)) // 2  # = 90
        self.equipment_slots = []


        slot_size = 46
        slot_padding = 4
        slot_names = [
            "head", "shoulders", "chest", "gloves", "legs", "boots",
            "amulet", "ring", "bracelet", "belt", "primary", "secondary"
        ]

        window_width = pygame.display.get_surface().get_width()
        panel_x = window_width - 327 - 10  # 10px margin from right
        panel_y = self.grid_origin_y  # Same vertical origin as inventory

        self.char_panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect((panel_x, panel_y), (327, 444)),
            manager=self.manager
        )

        # Frame background
        self.char_frame_bg = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect((0, 0), (327, 444)),
            image_surface=CHAR_FRAME_IMAGE,
            manager=self.manager,
            container=self.char_panel
        )

        vertical_slot_y = (444 - 292) // 2  # == 76
        # Left slots background
        self.left_slots_bg = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect((4, self.equip_slot_origin_y), (52, 264)),
            image_surface=pygame.transform.scale(CHAR_VERTICAL_SLOTS, (52, 264)),
            manager=self.manager,
            container=self.char_panel
        )
        #Right slots background
        self.right_slots_bg = pygame_gui.elements.UIImage(
            relative_rect=pygame.Rect((327 - 52 - 4, self.equip_slot_origin_y), (52, 264)),
            image_surface=pygame.transform.scale(CHAR_VERTICAL_SLOTS, (52, 264)),
            manager=self.manager,
            container=self.char_panel
        )

        # Left column (first 6 slots)
        for i in range(6):
            y = self.equip_slot_origin_y + (i * (self.equip_slot_size + self.equip_slot_padding))
            slot_panel = pygame_gui.elements.UIPanel(
                relative_rect=pygame.Rect((8, y), (44, 44)),
                manager=self.manager,
                container=self.char_panel
            )
            slot_panel.slot_type = slot_names[i]
            self.equipment_slots.append(slot_panel)

        # Right column (last 6 slots)
        for i in range(6):
            y = self.equip_slot_origin_y + i * (self.equip_slot_size + self.equip_slot_padding)
            x = 327 - 52
            slot_panel = pygame_gui.elements.UIPanel(
                relative_rect=pygame.Rect((x, y), (44, 44)),
                manager=self.manager,
                container=self.char_panel
            )
            slot_panel.slot_type = slot_names[i + 6]
            self.equipment_slots.append(slot_panel)

        # Find secondary slot reference for later greying out
        self.secondary_slot_panel = next((s for s in self.equipment_slots if s.slot_type == "secondary"), None)

        # Tooltip for equipped items (initially hidden)
        self.equip_tooltip_box = pygame_gui.elements.UITextBox(
            html_text="",
            relative_rect=pygame.Rect((self.char_panel.get_relative_rect().left - 210, self.grid_origin_y), (200, 200)),
            manager=self.manager
        )
        self.equip_tooltip_box.hide()

        self._create_stat_display()
        self.update_secondary_slot_visual()

    def _create_stat_display(self):
        self.stats_box = pygame_gui.elements.UITextBox(
            html_text="",
            relative_rect=Rect((68, 120), (190, 200)),
            manager=self.manager,
            container=self.char_panel
        )
        self.refresh_stat_display()
        # stat_lines = []
        # for stat, val in self.player.total_stats.items():
        #     val_display = f"{val:.1f}%" if isinstance(val, float) else str(val)
        #     stat_lines.append(f"<b>{stat.title()}</b>: {val_display}")
        # stats_html = "<br>".join(stat_lines)
        #
        # self.stats_box = pygame_gui.elements.UITextBox(
        #     html_text=stats_html,
        #     relative_rect=Rect((68, 120), (190, 200)),
        #     manager=self.manager,
        #     container=self.char_panel
        # )
        self.refresh_stat_display()

    def refresh_stat_display(self):
        self.player.recalculate_stats()
        stats = self.player.total_stats

        # Exclude certain stats from being shown
        hidden_stats = {
            "base_health", "base_mana",
            "Bonus Damage", "Bonus Health", "Bonus Mana"
        }

        # Define the stat order you want explicitly
        ordered_stats = [
            "Health", "Mana",
            "Strength", "Dexterity", "Intelligence", "Vitality",
            "Armor", "Block", "Dodge",
            "Critical Chance", "Critical Damage",
            "Attack Speed"
        ]

        stat_lines = []
        for stat in ordered_stats:
            if stat in self.player.total_stats and stat not in hidden_stats:
                val = self.player.total_stats[stat]
                val_display = f"{val:.1f}%" if isinstance(val, float) else str(val)
                stat_lines.append(f"<b>{stat}</b>: {val_display}")

        self.stats_box.set_text("<br>".join(stat_lines))

    def refresh_coin_display(self):
        if hasattr(self, "coin_label"):
            self.coin_label.set_text(f"Coins: {self.player.format_coins()}")

    def render_inventory_icons(self):
        # Clear existing icons first
        for icon in self.slot_icons:
            icon.kill()
        self.slot_icons = []

        for item in self.inventory_data:
            slot = item.get("slot")

            # Determine target container
            if isinstance(slot, int) and 0 <= slot < len(self.inventory_slots):
                container = self.inventory_slots[slot]
            elif isinstance(slot, str) and slot.startswith("equipped:"):
                slot_type = slot.split(":")[1]
                container = next((p for p in self.equipment_slots if p.slot_type == slot_type), None)
                if container is None:
                    continue
            else:
                continue

            try:
                icon_surface = pygame.image.load(item["icon"]).convert_alpha()
                icon_surface = pygame.transform.scale(icon_surface, (40, 40))  # Slightly smaller to fit in border

                # Get rarity color
                rarity = item.get("rarity", "Common")
                color_hex = rarity_colors.get(rarity, "#ffffff")
                color_rgb = pygame.Color(color_hex)

                # Create border surface (44x44) and fill with border color
                border_surface = pygame.Surface((44, 44), pygame.SRCALPHA)
                border_surface.fill((0, 0, 0, 0))  # transparent background
                pygame.draw.rect(border_surface, color_rgb, pygame.Rect(0, 0, 44, 44), border_radius=4)

                # Blit icon onto border surface (centered)
                border_surface.blit(icon_surface, (2, 2))  # offset to center

                # Create UIImage using the final composite
                icon = pygame_gui.elements.UIImage(
                    relative_rect=pygame.Rect((1, 1), (42, 42)),
                    image_surface=border_surface,
                    manager=self.manager,
                    container=container,
                )
                icon.slot_index = slot
                self.slot_icons.append(icon)
            except Exception as e:
                print(f"[Inventory] Failed to render icon for {item['name']}: {e}")

    def update_secondary_slot_visual(self):
        # Check what is equipped in primary
        primary_item = self.player.equipment.get("primary")
        is_two_handed = primary_item and primary_item.get("weapon_type") in ("Bow", "Staff")

        if is_two_handed:
            # Draw gray overlay
            overlay = pygame.Surface((44, 44), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))  # Semi-transparent black
            self.secondary_slot_overlay = pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect((0, 0), (44, 44)),
                image_surface=overlay,
                manager=self.manager,
                container=self.secondary_slot_panel
            )
        else:
            if hasattr(self, "secondary_slot_overlay"):
                self.secondary_slot_overlay.kill()
                del self.secondary_slot_overlay

    def draw_item_auras(self, surface):
        for icon in self.slot_icons:
            rarity = next((item["rarity"] for item in self.inventory_data if item["slot"] == icon.slot_index), None)
            if rarity not in ("Legendary", "Mythical"):
                continue  # Skip if not glow-worthy

            color_hex = rarity_colors.get(rarity)
            if not color_hex:
                continue

            glow_color = pygame.Color(color_hex)
            glow_color.a = 0  # We'll handle alpha manually

            icon_rect = icon.get_abs_rect()
            icon_center = icon_rect.center

            for i in range(8):  # Number of blur layers
                alpha = max(0, 60 - i * 7)  # Strong center, fading out
                radius = 18 + i * 2  # Increasing blur radius
                aura_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(aura_surface, (*glow_color[:3], alpha), (radius, radius), radius)
                surface.blit(aura_surface, (icon_center[0] - radius, icon_center[1] - radius))

    def teardown(self):
        self.back_button.kill()
        self.title_label.kill()
        if self.player.chat_window:
            self.player.chat_window.teardown()
            self.player.chat_window = None
        if hasattr(self, "coin_label"):
            self.coin_label.kill()

        ####### Inventory #######
        for btn in self.inventory_slots:
            btn.kill()
        self.inventory_slots = []
        for row in self.inventory_rows:
            row.kill()
        self.inventory_rows = []
        if hasattr(self, "bg_image"):
            self.bg_image.kill()
        if hasattr(self, "inventory_container"):
            self.inventory_container.kill()
        for icon in self.slot_icons:
            icon.kill()
        self.slot_icons = []

        ####### Character Sheet #######
        if hasattr(self, "char_panel"):
            self.char_panel.kill()
        if hasattr(self, "char_frame_bg"):
            self.char_frame_bg.kill()
        if hasattr(self, "left_slots_bg"):
            self.left_slots_bg.kill()
        if hasattr(self, "right_slots_bg"):
            self.right_slots_bg.kill()
        for slot in getattr(self, "equipment_slots", []):
            slot.kill()
        self.equipment_slots = []
        if hasattr(self, "equip_tooltip_box"):
            self.equip_tooltip_box.kill()

    def _save_inventory(self):
        try:
            payload = {
                "character_name": self.screen_manager.player.name,
                "inventory": self.inventory_data
            }
            response = requests.post(f"{SERVER_URL}/inventory/update", json=payload, timeout=5)
            response.raise_for_status()
        except Exception as e:
            print(f"[Inventory] Failed to update inventory: {e}")

    def sync_equipment_to_player(self):
        self.player.equipment = {
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

        for item in self.inventory_data:
            slot = item.get("slot")
            if isinstance(slot, str) and slot.startswith("equipped:"):
                subtype = slot.split(":")[1]
                if subtype in self.player.equipment:
                    self.player.equipment[subtype] = item

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                from screens.main_game_screen import MainGameScreen
                self.screen_manager.set_screen(MainGameScreen(self.manager, self.screen_manager))

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()

            # Check inventory slots
            for i, slot in enumerate(self.inventory_slots):
                if slot.get_abs_rect().collidepoint(mouse_pos):
                    for icon in self.slot_icons:
                        if getattr(icon, "slot_index", None) == i:
                            self.dragging_item = icon
                            self.dragging_index = i
                            self.slot_icons.remove(icon)
                            icon.kill()
                            return  # Exit early

            # Check equipped slots
            for slot in self.equipment_slots:
                if slot.get_abs_rect().collidepoint(mouse_pos):
                    slot_type = slot.slot_type
                    equipped_key = f"equipped:{slot_type}"

                    # Check if inventory has at least one free slot
                    used_slots = {item.get("slot") for item in self.inventory_data if isinstance(item.get("slot"), int)}
                    all_slots = set(range(len(self.inventory_slots)))
                    free_slots = all_slots - used_slots

                    if not free_slots:
                        print("[Equip] Cannot drag item — inventory is full.")
                        return  # Don't allow drag if inventory is full

                    for icon in self.slot_icons:
                        if getattr(icon, "slot_index", None) == equipped_key:
                            self.dragging_item = icon
                            self.dragging_index = equipped_key
                            self.slot_icons.remove(icon)
                            icon.kill()
                            return

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging_item:
                mouse_pos = pygame.mouse.get_pos()
                drop_index = None

                # First, check if dropped onto an inventory slot
                for i, slot in enumerate(self.inventory_slots):
                    if slot.get_abs_rect().collidepoint(mouse_pos):
                        drop_index = i
                        break

                # Then, check if dropped onto an equipment slot
                if drop_index is None:
                    for slot_panel in self.equipment_slots:
                        if slot_panel.get_abs_rect().collidepoint(mouse_pos):
                            drop_index = f"equipped:{slot_panel.slot_type}"
                            break

                # Before equipping into secondary slot:
                if drop_index == "equipped:secondary" and self.player.is_two_handed_weapon_equipped():
                    print("[Equip] Cannot equip secondary item with 2-handed weapon.")
                    drop_index = self.dragging_index  # Cancel drop

                # If dropped outside both, return to original
                if drop_index is None:
                    drop_index = self.dragging_index

                # Find dragged item
                dragged_item = next((item for item in self.inventory_data if item.get("slot") == self.dragging_index),
                                    None)

                # Check slot validity for equipment
                if isinstance(drop_index, str) and drop_index.startswith("equipped:"):
                    slot_type = drop_index.split(":")[1]
                    if dragged_item.get("subtype") != slot_type:
                        print(f"[Equip] Invalid: {dragged_item['subtype']} can't go into {slot_type}")
                        drop_index = self.dragging_index  # Cancel

                # Find item already in the drop slot (if any)
                existing_item = next((item for item in self.inventory_data if item.get("slot") == drop_index), None)

                # Swap slots
                if dragged_item:
                    dragged_item["slot"] = drop_index
                if existing_item:
                    existing_item["slot"] = self.dragging_index

                # Remove existing icons in both slots (inventory or equipment)
                slots_to_clear = (drop_index, self.dragging_index)
                icons_to_kill = [icon for icon in self.slot_icons if
                                 getattr(icon, "slot_index", None) in slots_to_clear]

                self.render_inventory_icons()

                # Save changes to server
                try:
                    payload = {
                        "character_name": self.screen_manager.player.name,
                        "inventory": self.inventory_data
                    }
                    response = requests.post(f"{SERVER_URL}/inventory/update", json=payload, timeout=5)
                    response.raise_for_status()
                except Exception as e:
                    print(f"[Inventory] Failed to update inventory: {e}")

                self.dragging_item = None
                self.dragging_index = None

                self.sync_equipment_to_player()
                self.player.save_stats_and_equipment()
                self.update_secondary_slot_visual()
                self.refresh_stat_display()

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            mouse_pos = pygame.mouse.get_pos()

            ####### Right-click Inventory Item to Equip ########
            for i, slot in enumerate(self.inventory_slots):
                if slot.get_abs_rect().collidepoint(mouse_pos):
                    item = next((item for item in self.inventory_data if item.get("slot") == i), None)
                    if item:
                        subtype = item.get("subtype")
                        if subtype:
                            equip_key = f"equipped:{subtype}"
                            equipped_item = next((itm for itm in self.inventory_data if itm.get("slot") == equip_key),
                                                 None)

                            # 🚫 BLOCK equipping to secondary if 2-handed weapon is equipped
                            if subtype == "secondary" and self.player.is_two_handed_weapon_equipped():
                                print("[Equip] Cannot equip secondary item while a 2-handed weapon is equipped.")
                                return  # Cancel the right-click equip

                            equipped_item = next((itm for itm in self.inventory_data if itm.get("slot") == equip_key),
                                                 None)

                            # Equip current item
                            item["slot"] = equip_key

                            # If something is already equipped, move it BACK to the same inventory slot
                            if equipped_item:
                                equipped_item["slot"] = i

                            self.render_inventory_icons()
                            self.sync_equipment_to_player()
                            self.player.save_stats_and_equipment()
                            self.update_secondary_slot_visual()
                            self.refresh_stat_display()
                            self._save_inventory()
                    return

            ####### Right-click Equipped Item to Unequip ########
            for slot_panel in self.equipment_slots:
                if slot_panel.get_abs_rect().collidepoint(mouse_pos):
                    equip_key = f"equipped:{slot_panel.slot_type}"
                    equipped_item = next((itm for itm in self.inventory_data if itm.get("slot") == equip_key), None)

                    if equipped_item:
                        # Try to put it in the first open inventory slot
                        used_slots = {itm.get("slot") for itm in self.inventory_data if
                                      isinstance(itm.get("slot"), int)}
                        all_slots = set(range(len(self.inventory_slots)))
                        free_slots = list(all_slots - used_slots)

                        if not free_slots:
                            print("[Right-click] Cannot unequip — inventory is full.")
                            return

                        equipped_item["slot"] = free_slots[0]  # Move back to inventory
                        self.render_inventory_icons()
                        self.sync_equipment_to_player()
                        self.player.save_stats_and_equipment()
                        self.update_secondary_slot_visual()
                        self.refresh_stat_display()
                        self._save_inventory()
                    return
            self.refresh_stat_display()

        if self.player.chat_window:
            self.player.chat_window.process_event(event)

    def update(self, time_delta):
        mouse_pos = pygame.mouse.get_pos()
        hovered_index = None
        hovered_inventory_item = None

        # Step 1: Hovering inventory slot?
        for i, slot in enumerate(self.inventory_slots):
            if slot.get_abs_rect().collidepoint(mouse_pos):
                hovered_index = i
                break

        # Step 2: Find item in inventory
        if hovered_index is not None:
            for item in self.inventory_data:
                if item.get("slot") == hovered_index:
                    hovered_inventory_item = item
                    break

        inventory_tooltip_text = None
        equipped_tooltip_text = None

        # Step 3: If hovering inventory item
        if hovered_inventory_item:
            rarity = hovered_inventory_item.get("rarity", "Common")
            color = rarity_colors.get(rarity, "#ffffff")
            inventory_tooltip_text = f"<b>{hovered_inventory_item['name']}</b><br><i><font color='{color}'>{rarity}</font></i>"

            stats = hovered_inventory_item.get("stats", {})
            subtype = hovered_inventory_item.get("subtype")

            equipped_item = None
            if subtype:
                equipped_key = f"equipped:{subtype}"
                equipped_item = next((item for item in self.inventory_data if item.get("slot") == equipped_key), None)

            for stat, val in stats.items():
                stat_line = f"{stat.title()}: {val}"

                if equipped_item and stat in equipped_item.get("stats", {}):
                    equipped_val = equipped_item["stats"][stat]
                    if val > equipped_val:
                        stat_line = f"<font color='#00ff00'>{stat_line}</font>"  # Green
                    elif val < equipped_val:
                        stat_line = f"<font color='#ff0000'>{stat_line}</font>"  # Red

                inventory_tooltip_text += f"<br>{stat_line}"

            # Step 4: Build equipped tooltip (if exists)
            if equipped_item:
                rarity = equipped_item.get("rarity", "Common")
                color = rarity_colors.get(rarity, "#ffffff")
                equipped_tooltip_text = f"<b>{equipped_item['name']}</b><br><i><font color='{color}'>{rarity}</font></i>"
                for stat, val in equipped_item.get("stats", {}).items():
                    equipped_tooltip_text += f"<br>{stat.title()}: {val}"

        # Step 5: Fallback: check hovering equipment slots (only if not hovering inventory)
        elif hovered_index is None:
            for slot in self.equipment_slots:
                if slot.get_abs_rect().collidepoint(mouse_pos):
                    slot_type = slot.slot_type
                    equipped_item = next(
                        (item for item in self.inventory_data if item.get("slot") == f"equipped:{slot_type}"), None)
                    if equipped_item:
                        rarity = equipped_item.get("rarity", "Common")
                        color = rarity_colors.get(rarity, "#ffffff")
                        equipped_tooltip_text = f"<b>{equipped_item['name']}</b><br><i><font color='{color}'>{rarity}</font></i>"
                        for stat, val in equipped_item.get("stats", {}).items():
                            equipped_tooltip_text += f"<br>{stat.title()}: {val}"
                    break

        # Step 6: Apply tooltips
        if inventory_tooltip_text:
            self.hover_tooltip_box.set_text(inventory_tooltip_text)
            self.hover_tooltip_box.show()
        else:
            self.hover_tooltip_box.hide()

        if equipped_tooltip_text:
            self.equip_tooltip_box.set_text(equipped_tooltip_text)
            self.equip_tooltip_box.show()
        else:
            self.equip_tooltip_box.hide()

        if self.player.chat_window:
            self.player.chat_window.update(time_delta)

    def draw(self, window_surface):


        self.manager.draw_ui(window_surface)
        self.draw_item_auras(window_surface)

        if self.dragging_item:
            mx, my = pygame.mouse.get_pos()
            window_surface.blit(self.dragging_item.image, (mx - 21, my - 21))  # Center under cursor


ScreenRegistry.register("inventory", InventoryScreen)