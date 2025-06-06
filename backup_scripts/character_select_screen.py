from player import Player
from screen_manager import *
import pygame
import pygame_gui
from screen_registry import ScreenRegistry
import os

class ConfirmDeletePopup:
    def __init__(self, manager, character_name, callback_confirm, callback_cancel):
        self.manager = manager
        self.character_name = character_name
        self.callback_confirm = callback_confirm
        self.callback_cancel = callback_cancel

        self.window = pygame_gui.elements.UIWindow(
            rect=pygame.Rect((400, 250), (300, 260)),
            manager=self.manager,
            window_display_title="Confirm Deletion",
            object_id="#confirm_delete_popup"
        )

        self.message_label = pygame_gui.elements.UITextBox(
            html_text=f"Delete '{character_name}'?<br>This cannot be undone.",
            relative_rect=pygame.Rect((10, 10), (280, 100)),
            manager=self.manager,
            container=self.window
        )

        self.yes_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((30, 170), (100, 50)),  # Y moved down to 170
            text="Yes",
            manager=self.manager,
            container=self.window
        )

        self.cancel_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((170, 170), (100, 50)),  # Y moved down to 170
            text="Cancel",
            manager=self.manager,
            container=self.window
        )

    def process_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.yes_button:
                self.callback_confirm(self.character_name)
                self.window.kill()

            elif event.ui_element == self.cancel_button:
                self.callback_cancel()
                self.window.kill()

class CharacterSelectScreen(BaseScreen):
    def setup(self):
        # Load character names
        character_names = self.load_character_names()
        self.confirm_popup = None

        self.character_list = pygame_gui.elements.UISelectionList(
            relative_rect=pygame.Rect((250, 150), (300, 300)),
            item_list=character_names,
            manager=self.manager
        )

        self.new_character_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((250, 470), (140, 50)),
            text="New Character",
            manager=self.manager
        )

        self.select_character_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((410, 470), (140, 50)),
            text="Select Character",
            manager=self.manager
        )

        self.message_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((250, 530), (300, 30)),
            text="Select or Create a Character",
            manager=self.manager
        )
        self.delete_character_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((250, 530), (300, 50)),
            text="Delete Character",
            manager=self.manager
        )

    def load_character_names(self):
        characters_dir = os.path.join('Save_Data', 'Characters')
        if not os.path.exists(characters_dir):
            return []

        names = []
        for filename in os.listdir(characters_dir):
            if filename.endswith(".json"):
                names.append(filename[:-5])  # remove ".json"
        return names

    def delete_character(self, name):
        import os

        save_path = os.path.join('Save_Data', 'Characters', f"{name}.json")
        if os.path.exists(save_path):
            os.remove(save_path)

        # Refresh character list
        character_names = self.load_character_names()
        self.character_list.set_item_list(character_names)
        self.message_label.set_text(f"Character '{name}' deleted.")

    def confirm_delete(self, name):
        self.confirm_popup = None  # <<< Reset
        self.delete_character(name)

    def cancel_delete(self):
        self.confirm_popup = None  # <<< Just reset, no deletion

    def teardown(self):
        self.character_list.kill()
        self.new_character_button.kill()
        self.select_character_button.kill()
        self.message_label.kill()
        self.delete_character_button.kill()

    def handle_event(self, event):
        if self.confirm_popup:
            self.confirm_popup.process_event(event)
            return  # <<< Don't process other stuff if popup is open

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.new_character_button:
                character_creation_class = ScreenRegistry.get("character_creation")
                if character_creation_class:
                    self.screen_manager.set_screen(character_creation_class(self.manager, self.screen_manager))

            elif event.ui_element == self.select_character_button:
                selected_character_name = self.character_list.get_single_selection()
                if selected_character_name:
                    from player import Player
                    self.screen_manager.player = Player.load(selected_character_name)

                    # After loading, go to main game screen
                    main_game_screen_class = ScreenRegistry.get("main_game")
                    if main_game_screen_class:
                        self.screen_manager.set_screen(main_game_screen_class(self.manager, self.screen_manager))

            elif event.ui_element == self.delete_character_button:
                selected_character_name = self.character_list.get_single_selection()
                if selected_character_name and not self.confirm_popup:
                    self.confirm_popup = ConfirmDeletePopup(
                        self.manager,
                        selected_character_name,
                        self.confirm_delete,
                        self.cancel_delete
                    )

    def update(self, time_delta):
        self.manager.update(time_delta)

    def draw(self, window_surface):
        self.manager.draw_ui(window_surface)

ScreenRegistry.register("character_select", CharacterSelectScreen)

