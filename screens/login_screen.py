from screen_manager import BaseScreen
from screen_registry import ScreenRegistry
from account_manager import AccountManager
from screen_registry import ScreenRegistry
import pygame_gui
import pygame
import os
import json

class LoginScreen(BaseScreen):
    def __init__(self, manager, screen_manager):
        super().__init__(manager, screen_manager)
        self.clicked_this_frame = False
        self.remember_me_checked = False  # <<< Track checkbox state manually

    def setup(self):
        self.account_manager = AccountManager()

        self.login_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((250, 100), (300, 50)),
            text="Login",
            manager=self.manager
        )

        self.username_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((250, 170), (300, 50)),
            manager=self.manager
        )
        self.username_entry.focus()

        self.password_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((250, 240), (300, 50)),
            manager=self.manager
        )
        self.password_entry.set_text_hidden(True)

        self.login_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((250, 310), (145, 50)),
            text="Login",
            manager=self.manager
        )

        self.register_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((405, 310), (145, 50)),
            text="Register",
            manager=self.manager
        )

        self.message_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((250, 380), (300, 30)),
            text="",
            manager=self.manager
        )

        self.remember_me_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((250, 410), (30, 30)),
            text='',
            manager=self.manager
        )

        self.remember_me_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((290, 410), (100, 30)),
            text='Remember Me',
            manager=self.manager
        )



        self.load_remembered_login() #Make sure this is at the end of setup

    def teardown(self):
        self.login_label.kill()
        self.username_entry.kill()
        self.password_entry.kill()
        self.login_button.kill()
        self.register_button.kill()
        self.message_label.kill()
        self.remember_me_button.kill()
        self.remember_me_label.kill()

    def load_remembered_login(self):
        save_path = os.path.join('Save_Data', 'login_info.json')
        if os.path.exists(save_path):
            with open(save_path, 'r') as f:
                data = json.load(f)
                remembered_username = data.get("username", "")
                remember_me_flag = data.get("remember_me", False)

                self.username_entry.set_text(remembered_username)
                if remember_me_flag:
                    self.remember_me_checked = True
                    self.remember_me_button.set_text('X')
                else:
                    self.remember_me_checked = False
                    self.remember_me_button.set_text('')

    def save_remembered_login(self, username):
        save_dir = 'Save_Data'
        os.makedirs(save_dir, exist_ok=True)

        save_path = os.path.join(save_dir, 'login_info.json')
        with open(save_path, 'w') as f:
            json.dump({
                "username": username,
                "remember_me": True
            }, f)

    def clear_remembered_login(self):
        save_path = os.path.join('Save_Data', 'login_info.json')
        if os.path.exists(save_path):
            os.remove(save_path)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                if self.username_entry.is_focused:
                    self.username_entry.unfocus()
                    self.password_entry.focus()
                elif self.password_entry.is_focused:
                    self.password_entry.unfocus()
                    self.username_entry.focus()

            elif event.key == pygame.K_RETURN:
                username = self.username_entry.get_text().strip()
                password = self.password_entry.get_text().strip()
                if self.account_manager.login(username, password):
                    self.message_label.set_text("Login successful!")

                    # <<< Save Remember Me info BEFORE switching screens
                    if self.remember_me_checked:
                        self.save_remembered_login(username)
                    else:
                        self.clear_remembered_login()

                    # <<< Now switch screens
                    character_select_screen_class = ScreenRegistry.get("character_select")
                    if character_select_screen_class:
                        self.screen_manager.set_screen(character_select_screen_class(self.manager, self.screen_manager))
                else:
                    self.message_label.set_text("Login failed. Try again.")

        elif event.type == pygame_gui.UI_BUTTON_PRESSED:

            if event.ui_element == self.remember_me_button:
                self.remember_me_checked = not self.remember_me_checked
                if self.remember_me_checked:
                    self.remember_me_button.set_text('x')
                    self.remember_me_button.select()
                else:
                    self.remember_me_button.set_text('')
                    self.remember_me_button.unselect()


            username = self.username_entry.get_text().strip()
            password = self.password_entry.get_text().strip()

            if not username or not password:
                self.message_label.set_text("Username and password required.")
            elif event.ui_element == self.login_button:
                if self.account_manager.login(username, password):
                    self.message_label.set_text("Login successful!")
                    # <<< Save Remember Me info BEFORE switching screens
                    if self.remember_me_checked:
                        self.save_remembered_login(username)
                    else:
                        self.clear_remembered_login()
                    # <<< Now switch screens
                    character_select_screen_class = ScreenRegistry.get("character_select")
                    if character_select_screen_class:
                        self.screen_manager.set_screen(character_select_screen_class(self.manager, self.screen_manager))
                else:
                    self.message_label.set_text("Invalid credentials.")
            elif event.ui_element == self.register_button:
                if username in self.account_manager.accounts:
                    self.message_label.set_text("User already exists.")
                else:
                    self.account_manager.register(username, password)
                    self.message_label.set_text("Account created! You can now login.")

    def update(self, time_delta):
        self.manager.update(time_delta)

    def draw(self, window_surface):
        self.manager.draw_ui(window_surface)

# 🚀 Register this screen
ScreenRegistry.register("login", LoginScreen)