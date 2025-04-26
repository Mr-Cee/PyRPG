# screens/character_creation_screen.py

from screen_manager import BaseScreen
from screen_registry import ScreenRegistry
import pygame
import pygame_gui
import os
import json

class CharacterCreationScreen(BaseScreen):
    def setup(self):
        self.name_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((250, 150), (300, 50)),
            manager=self.manager
        )
        self.name_entry.set_text("Enter Character Name")

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
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.create_button:
                name = self.name_entry.get_text().strip()
                char_class = self.class_dropdown.selected_option

                if not name:
                    self.message_label.set_text("Please enter a name.")
                else:
                    self.save_character(name, char_class)
                    self.message_label.set_text(f"Character {name} created!")

                    # After creating, go back to Character Select screen
                    from screen_registry import ScreenRegistry
                    char_select_class = ScreenRegistry.get("character_select")
                    if char_select_class:
                        self.screen_manager.set_screen(char_select_class(self.manager, self.screen_manager))

            elif event.ui_element == self.cancel_button:
                from screen_registry import ScreenRegistry
                char_select_class = ScreenRegistry.get("character_select")
                if char_select_class:
                    self.screen_manager.set_screen(char_select_class(self.manager, self.screen_manager))

    def save_character(self, name, char_class):
        os.makedirs('Save_Data/Characters', exist_ok=True)
        character_data = {
            "name": name,
            "char_class": char_class,  # <<< now matches Player.load
            "level": 1,
            "experience": 0
        }

        save_path = os.path.join('Save_Data', 'Characters', f"{name}.json")
        with open(save_path, 'w') as f:
            json.dump(character_data, f)

    def update(self, time_delta):
        self.manager.update(time_delta)

    def draw(self, window_surface):
        self.manager.draw_ui(window_surface)

# 🚀 Register the screen
ScreenRegistry.register("character_creation", CharacterCreationScreen)