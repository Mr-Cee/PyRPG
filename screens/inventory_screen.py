import pygame
import pygame_gui
from pygame import Rect
import requests
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
        self.dragging_item = None
        self.dragging_index = None
        self.drag_icon = None
        self.hovered_slot_index = None
        self.tooltip = None

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

        self.setup_inventory()
        self.setup_character_sheet()

    def setup_inventory(self):
        # Setting up Grid
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
                # slot_button = pygame_gui.elements.UIButton(
                #     relative_rect=pygame.Rect((slot_x, 3), (46, 46)),  # 3px top padding
                #     text="",
                #     manager=self.manager,
                #     container=row_panel
                # )
                # self.inventory_slots.append(slot_button)

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

        # Display items in UI
        for item in inventory_data:
            slot_index = item.get("slot")
            if slot_index is None or not (0 <= slot_index < len(self.inventory_slots)):
                print(f"[Inventory] Skipping item with invalid slot: {item}")
                continue

            slot_button = self.inventory_slots[slot_index]
            if slot_button is None or not hasattr(slot_button, "rect"):
                print(f"[Inventory] Slot {slot_index} has no valid container.")
                continue

            slot_index = item.get("slot")
            item["slot"] = slot_index
            if 0 <= slot_index < len(self.inventory_slots):
                slot_button = self.inventory_slots[slot_index]

                if "icon" in item and slot_button is not None:
                    slot_container = self.inventory_slots[slot_index]

                    # Load icon and place inside the slot panel
                    try:
                        icon_surface = pygame.image.load(item["icon"]).convert_alpha()
                        icon_surface = pygame.transform.scale(icon_surface, (42, 42))
                        icon = pygame_gui.elements.UIImage(
                            relative_rect=pygame.Rect((2, 2), (42, 42)),
                            image_surface=icon_surface,
                            manager=self.manager,
                            container=slot_container,
                        )
                        icon.slot_index = slot_index
                        self.slot_icons.append(icon)

                    except Exception as e:
                        print(f"[Inventory] Failed to load icon for slot {slot_index}: {e}")
                else:
                    label = pygame_gui.elements.UILabel(
                        relative_rect=pygame.Rect((0, 0), (46, 46)),
                        text=item.get("name", "?"),
                        manager=self.manager,
                        container=slot_button
                    )
                    icon.slot_index = slot_index
                    self.slot_icons.append(label)

        self.hover_tooltip_box = pygame_gui.elements.UITextBox(
            html_text="",
            relative_rect=pygame.Rect((330, 60), (200, 200)),  # Adjust position/size as needed
            manager=self.manager
        )
        self.hover_tooltip_box.hide()

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

    def teardown(self):
        self.back_button.kill()
        self.title_label.kill()

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

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                from screens.main_game_screen import MainGameScreen
                self.screen_manager.set_screen(MainGameScreen(self.manager, self.screen_manager))

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()

            for i, slot in enumerate(self.inventory_slots):

                slot_rect = slot.get_abs_rect()
                if slot_rect.collidepoint(mouse_pos):

                    for icon in self.slot_icons:
                        if getattr(icon, "slot_index", None) == i:

                            self.dragging_item = icon
                            self.dragging_index = i
                            self.slot_icons.remove(icon)
                            icon.kill()
                            break

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging_item:
                # Determine where the item was dropped
                drop_index = None
                for i, slot in enumerate(self.inventory_slots):
                    slot_rect = slot.get_abs_rect()
                    if slot_rect.collidepoint(pygame.mouse.get_pos()):
                        drop_index = i
                        break

                # If dropped outside, return to original slot
                if drop_index is None:
                    drop_index = self.dragging_index

                # Find any item already in the drop slot
                existing_item = None
                for item in self.inventory_data:
                    if item.get("slot") == drop_index:
                        existing_item = item
                        break

                # Swap the slots in the data
                for item in self.inventory_data:
                    if item.get("slot") == self.dragging_index:
                        item["slot"] = drop_index
                        break
                if existing_item:
                    existing_item["slot"] = self.dragging_index

                # Remove any icons in both involved slots
                slots_to_clear = (drop_index, self.dragging_index)
                icons_to_kill = [icon for icon in self.slot_icons if
                                 getattr(icon, "slot_index", None) in slots_to_clear]
                for icon in icons_to_kill:
                    icon.kill()
                    self.slot_icons.remove(icon)

                # Re-render updated icons
                for item in self.inventory_data:
                    slot = item.get("slot")
                    if slot is not None and 0 <= slot < len(self.inventory_slots):
                        try:
                            icon_surface = pygame.image.load(item["icon"]).convert_alpha()
                            icon_surface = pygame.transform.scale(icon_surface, (42, 42))
                            icon = pygame_gui.elements.UIImage(
                                relative_rect=pygame.Rect((2, 2), (42, 42)),
                                image_surface=icon_surface,
                                manager=self.manager,
                                container=self.inventory_slots[slot],
                            )
                            icon.slot_index = slot
                            self.slot_icons.append(icon)
                        except Exception as e:
                            print(f"[Inventory] Failed to re-render icon: {e}")

                # Save to server
                try:
                    payload = {
                        "character_name": self.screen_manager.player.name,
                        "inventory": self.inventory_data
                    }
                    response = requests.post(f"{SERVER_URL}/inventory/update", json=payload, timeout=5)
                    response.raise_for_status()
                except Exception as e:
                    print(f"[Inventory] Failed to update inventory: {e}")

                # Reset drag state
                self.dragging_item = None
                self.dragging_index = None

    def update(self, time_delta):
        mouse_pos = pygame.mouse.get_pos()
        hovered_index = None

        for i, slot in enumerate(self.inventory_slots):
            if slot.get_abs_rect().collidepoint(mouse_pos):
                hovered_index = i
                break

        if hovered_index is not None:
            for item in self.inventory_data:
                if item.get("slot") == hovered_index:
                    rarity = item.get("rarity", "Common")
                    color = rarity_colors.get(rarity, "#ffffff")
                    tooltip_text = f"<b>{item['name']}</b><br><i><font color='{color}'>{item['rarity']}</font></i>"
                    for stat, val in item.get("stats", {}).items():
                        tooltip_text += f"<br>{stat.title()}: {val}"

                    self.hover_tooltip_box.set_text(tooltip_text)
                    self.hover_tooltip_box.show()
                    break
        else:
            self.hover_tooltip_box.hide()





    def draw(self, window_surface):
        self.manager.draw_ui(window_surface)

        if self.dragging_item:
            mx, my = pygame.mouse.get_pos()
            window_surface.blit(self.dragging_item.image, (mx - 21, my - 21))  # Center under cursor


ScreenRegistry.register("inventory", InventoryScreen)