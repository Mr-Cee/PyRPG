# screens/character_creation_screen.py

from screen_manager import BaseScreen
from screen_registry import ScreenRegistry
import pygame
import pygame_gui
import requests

from settings import SERVER_URL  # or wherever your server runs


class CharacterCreationScreen(BaseScreen):
    def __init__(self, manager, screen_manager):
        super().__init__(manager, screen_manager)
        self.name_placeholder = "Enter Character Name"
        self.name_has_been_edited = False

    def setup(self):
        self.name_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((250, 150), (300, 50)),
            manager=self.manager
        )
        self.name_entry.set_text(self.name_placeholder)

        self.class_dropdown = pygame_gui.elements.UIDropDownMenu(
            options_list=["Warrior", "Mage", "Rogue"],
            starting_option="Warrior",
            relative_rect=pygame.Rect((250, 220), (300, 50)),
            manager=self.manager
        )

        self.create_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((250, 300), (140, 50)),
            text="Create",
            manager=self.manager
        )

        self.cancel_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((410, 300), (140, 50)),
            text="Cancel",
            manager=self.manager
        )

        self.message_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((250, 370), (300, 30)),
            text="",
            manager=self.manager
        )

    def teardown(self):
        self.name_entry.kill()
        self.class_dropdown.kill()
        self.create_button.kill()
        self.cancel_button.kill()
        self.message_label.kill()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_TEXT_ENTRY_CHANGED:
            if event.ui_element == self.name_entry:
                if not self.name_has_been_edited and self.name_entry.get_text() != self.name_placeholder:
                    self.name_has_been_edited = True

        if event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED:
            if event.ui_element == self.name_entry:
                if self.name_entry.get_text().strip() == "":
                    self.name_entry.set_text(self.name_placeholder)
                    self.name_has_been_edited = False

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.create_button:
                self.attempt_create_character()

            elif event.ui_element == self.cancel_button:
                char_select_class = ScreenRegistry.get("character_select")
                if char_select_class:
                    self.screen_manager.set_screen(char_select_class(self.manager, self.screen_manager))

    def attempt_create_character(self):
        name = self.name_entry.get_text().strip()
        char_class = self.class_dropdown.selected_option
        if isinstance(char_class, (tuple, list)):
            char_class = char_class[0]


        if not name or name == self.name_placeholder:
            self.message_label.set_text("Please enter a name.")
            return

        headers = {"Authorization": f"Bearer {self.screen_manager.auth_token}"}

        new_character_data = {
            "name": name,
            "char_class": char_class,
            "level": 1,
            "experience": 0,
            "inventory": {},
            "equipment": {},
            "skills": {}
        }

        try:
            response = requests.post(
                f"{SERVER_URL}/player/{self.screen_manager.current_account}",
                json=new_character_data,
                headers=headers
            )

            if response.status_code == 200:
                print("✅ Character created successfully!")
                char_select_class = ScreenRegistry.get("character_select")
                if char_select_class:
                    self.screen_manager.set_screen(char_select_class(self.manager, self.screen_manager))
            else:
                print(f"❌ Character creation failed: {response.text}")
                self.message_label.set_text("Character creation failed.")

        except Exception as e:
            print(f"❌ Connection error: {e}")
            self.message_label.set_text("Connection error.")

    def update(self, time_delta):
        self.manager.update(time_delta)

        if self.name_entry.is_focused:
            if self.name_entry.get_text() == self.name_placeholder:
                self.name_entry.set_text("")
        else:
            if self.name_entry.get_text().strip() == "" or self.name_entry.get_text() is None:
                self.name_entry.set_text(self.name_placeholder)

    def draw(self, window_surface):
        self.manager.draw_ui(window_surface)

# 🚀 Register the screen
ScreenRegistry.register("character_creation", CharacterCreationScreen)
