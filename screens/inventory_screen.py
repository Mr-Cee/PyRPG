import pygame
import pygame_gui
from pygame import Rect
import requests
from settings import SERVER_URL
from screen_manager import BaseScreen
from screen_registry import ScreenRegistry

#Load and scale the background image once
INVENTORY_BG_IMAGE = pygame.image.load("Assets/GUI/Inventory/inner_carving.png").convert_alpha()
INVENTORY_BG_IMAGE = pygame.transform.scale(INVENTORY_BG_IMAGE, (302, 309))  # Match grid area
ROW_IMAGE = pygame.image.load("Assets/GUI/Inventory/row_slot.png").convert_alpha()



class InventoryScreen(BaseScreen):
    def __init__(self, manager, screen_manager):
        super().__init__(manager, screen_manager)

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


        #Setting up Grid
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
                slot_button = pygame_gui.elements.UIButton(
                    relative_rect=pygame.Rect((slot_x, 3), (46, 46)),  # 3px top padding
                    text="",
                    manager=self.manager,
                    container=row_panel
                )
                self.inventory_slots.append(slot_button)

        self.slot_icons = []

        # Fetch inventory data from backend
        player_name = self.screen_manager.player.name
        try:
            response = requests.get(f"{SERVER_URL}/inventory/{player_name}", timeout=5)
            response.raise_for_status()
            inventory_data = response.json()
        except Exception as e:
            print(f"[Inventory] Failed to load inventory: {e}")
            inventory_data = []  # fallback to empty

        # Display items in UI
        for item in inventory_data:
            slot_index = item.get("slot")
            if 0 <= slot_index < len(self.inventory_slots):
                slot_button = self.inventory_slots[slot_index]

                if "icon" in item:
                    try:
                        icon_surface = pygame.image.load(item["icon"]).convert_alpha()
                        icon_surface = pygame.transform.scale(icon_surface, (42, 42))
                        icon = pygame_gui.elements.UIImage(
                            relative_rect=pygame.Rect((2, 2), (42, 42)),
                            image_surface=icon_surface,
                            manager=self.manager,
                            container=slot_button
                        )
                        self.slot_icons.append(icon)
                    except Exception as e:
                        print(f"[Inventory] Failed to load icon: {e}")
                else:
                    label = pygame_gui.elements.UILabel(
                        relative_rect=pygame.Rect((0, 0), (46, 46)),
                        text=item.get("name", "?"),
                        manager=self.manager,
                        container=slot_button
                    )
                    self.slot_icons.append(label)



    def teardown(self):
        self.back_button.kill()
        self.title_label.kill()

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

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                from screens.main_game_screen import MainGameScreen
                self.screen_manager.set_screen(MainGameScreen(self.manager, self.screen_manager))
            elif event.ui_element in self.inventory_slots:
                index = self.inventory_slots.index(event.ui_element)
                print(f"[Inventory] Clicked slot #{index}")

    def update(self, time_delta):
        pass

    def draw(self, window_surface):
        self.manager.draw_ui(window_surface)


ScreenRegistry.register("inventory", InventoryScreen)