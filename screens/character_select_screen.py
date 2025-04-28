from player import Player
from screen_manager import *
import pygame
import pygame_gui
import requests
from screen_registry import ScreenRegistry

SERVER_URL = "http://localhost:8000"

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
            relative_rect=pygame.Rect((30, 170), (100, 50)),
            text="Yes",
            manager=self.manager,
            container=self.window
        )

        self.cancel_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((170, 170), (100, 50)),
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

class ConfirmDeleteAccountPopup:
    def __init__(self, manager, callback_confirm, callback_cancel):
        self.manager = manager
        self.callback_confirm = callback_confirm
        self.callback_cancel = callback_cancel

        self.window = pygame_gui.elements.UIWindow(
            rect=pygame.Rect((400, 250), (300, 260)),
            manager=self.manager,
            window_display_title="Delete Account",
            object_id="#confirm_delete_account_popup"
        )

        self.message_label = pygame_gui.elements.UITextBox(
            html_text="Delete your account and all characters?<br>This cannot be undone!",
            relative_rect=pygame.Rect((10, 10), (280, 100)),
            manager=self.manager,
            container=self.window
        )

        self.yes_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((30, 170), (100, 50)),
            text="Yes",
            manager=self.manager,
            container=self.window
        )

        self.cancel_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((170, 170), (100, 50)),
            text="Cancel",
            manager=self.manager,
            container=self.window
        )

    def process_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.yes_button:
                self.callback_confirm()
                self.window.kill()
            elif event.ui_element == self.cancel_button:
                self.callback_cancel()
                self.window.kill()

class CharacterSelectScreen(BaseScreen):
    def setup(self):
        self.confirm_popup = None
        self.character_data = None  # Store full character info

        self.character_list = pygame_gui.elements.UISelectionList(
            relative_rect=pygame.Rect((250, 150), (300, 300)),
            item_list=[],
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

        self.delete_character_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((250, 530), (300, 50)),
            text="Delete Character",
            manager=self.manager
        )

        self.message_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((250, 590), (300, 30)),
            text="Select or Create a Character",
            manager=self.manager
        )

        self.delete_account_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((10, 10), (150, 40)),
            text="Delete Account",
            manager=self.manager
        )

        self.load_character_from_server()

    def load_character_from_server(self):
        headers = {"Authorization": f"Bearer {self.screen_manager.auth_token}"}

        try:
            response = requests.get(
                f"{SERVER_URL}/player/{self.screen_manager.current_account}",
                headers=headers
            )

            if response.status_code == 200:
                # self.character_data = response.json()

                if response.status_code == 200:
                    data = response.json()
                    self.character_data = data

                    character_list_items = []
                    for char in self.character_data:
                        formatted_name = f"{char['name']}, the level {char['level']} {char['char_class']}"
                        character_list_items.append(formatted_name)

                    self.character_list.set_item_list(character_list_items)

                else:
                    print(f"❌ Failed to load characters: {response.text}")

        except Exception as e:
            print(f"❌ Failed to load character info: {e}")
            self.character_list.set_item_list([])
            self.message_label.set_text("Connection error.")

    def delete_character(self, name):
        headers = {"Authorization": f"Bearer {self.screen_manager.auth_token}"}

        try:
            response = requests.delete(
                f"{SERVER_URL}/player/{self.screen_manager.current_account}",
                headers=headers
            )

            if response.status_code == 200:
                print("✅ Character deleted successfully.")
                self.character_list.set_item_list([])
                self.message_label.set_text(f"Character '{name}' deleted.")

                self.load_character_from_server()
            else:
                print(f"❌ Failed to delete character: {response.text}")
                self.message_label.set_text("Failed to delete character.")

        except Exception as e:
            print(f"❌ Connection error during deletion: {e}")
            self.message_label.set_text("Connection error.")

    def confirm_delete(self, name):
        self.confirm_popup = None
        self.delete_character(name)

    def confirm_delete_account(self):
        headers = {"Authorization": f"Bearer {self.screen_manager.auth_token}"}
        try:
            response = requests.delete(
                f"{SERVER_URL}/account/{self.screen_manager.current_account}",
                headers=headers
            )
            if response.status_code == 200:
                print("✅ Account deleted successfully.")

                # Go back to login screen
                login_screen_class = ScreenRegistry.get("login")
                if login_screen_class:
                    self.screen_manager.set_screen(login_screen_class(self.manager, self.screen_manager))
            else:
                print(f"❌ Failed to delete account: {response.text}")
                self.message_label.set_text("Failed to delete account.")

        except Exception as e:
            print(f"❌ Connection error during account deletion: {e}")
            self.message_label.set_text("Connection error.")

    def cancel_delete(self):
        self.confirm_popup = None

    def teardown(self):
        self.character_list.kill()
        self.new_character_button.kill()
        self.select_character_button.kill()
        self.delete_character_button.kill()
        self.message_label.kill()
        self.delete_account_button.kill()

    def handle_event(self, event):
        if self.confirm_popup:
            self.confirm_popup.process_event(event)
            return

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
#Create Character
            if event.ui_element == self.new_character_button:
                character_creation_class = ScreenRegistry.get("character_creation")
                if character_creation_class:
                    self.screen_manager.set_screen(character_creation_class(self.manager, self.screen_manager))
#Select Character
            elif event.ui_element == self.select_character_button:
                selected_name = self.character_list.get_single_selection()
                if selected_name:
                    selected_name = selected_name.split(",")[0].strip()
                    # Find the correct character data
                    for char in self.character_data:
                        if char["name"] == selected_name:
                            self.screen_manager.player = Player.from_server_data(char)
                            break

                    main_game_screen_class = ScreenRegistry.get("main_game")
                    if main_game_screen_class:
                        self.screen_manager.set_screen(main_game_screen_class(self.manager, self.screen_manager))
#Delete Character
            elif event.ui_element == self.delete_character_button:
                selected_name = self.character_list.get_single_selection()
                if selected_name and not self.confirm_popup:
                    self.confirm_popup = ConfirmDeletePopup(
                        self.manager,
                        selected_name,
                        self.confirm_delete,
                        self.cancel_delete
                    )
#Delete Account
            elif event.ui_element == self.delete_account_button:
                if not self.confirm_popup:
                    self.confirm_popup = ConfirmDeleteAccountPopup(
                        self.manager,
                        self.confirm_delete_account,
                        self.cancel_delete
                    )

    def update(self, time_delta):
        self.manager.update(time_delta)

    def draw(self, surface):
        self.manager.draw_ui(surface)


ScreenRegistry.register("character_select", CharacterSelectScreen)
