import pygame
import pygame_gui
import requests
import threading
from screen_registry import ScreenRegistry

# Define SERVER_URL
SERVER_URL = "http://localhost:8000"

class LoginScreen:
    def __init__(self, manager, screen_manager):
        self.manager = manager
        self.screen_manager = screen_manager

        self.username_entry = None
        self.password_entry = None
        self.login_button = None
        self.register_button = None
        self.message_label = None
        self.remember_me_button = None
        self.remember_me_label = None

        self.forgot_password_button = None
        self.forgot_password_button_created = False

        self.connecting = False
        self.awaiting_login = False
        self.login_thread = None
        self.login_result = None

    def setup(self):
        self.username_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((250, 200), (300, 50)),
            manager=self.manager
        )
        self.password_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((250, 260), (300, 50)),
            manager=self.manager
        )
        self.password_entry.set_text_hidden(True)

        self.login_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((250, 320), (145, 50)),
            text="Login",
            manager=self.manager
        )

        self.register_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((405, 320), (145, 50)),
            text="Register",
            manager=self.manager
        )

        self.message_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((250, 380), (300, 30)),
            text="",
            manager=self.manager
        )

        self.remember_me_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((250, 420), (30, 30)),
            text="",
            manager=self.manager
        )
        self.remember_me_button.select()

        self.remember_me_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((290, 420), (260, 30)),
            text="Remember Me",
            manager=self.manager
        )

    def teardown(self):
        for element in [self.username_entry, self.password_entry, self.login_button,
                        self.register_button, self.message_label, self.remember_me_button,
                        self.remember_me_label]:
            if element:
                element.kill()

        if self.forgot_password_button:
            self.forgot_password_button.kill()

        if hasattr(self, 'register_popup') and self.register_popup:
            self.register_popup.kill()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.login_button:
                username = self.username_entry.get_text().strip()
                password = self.password_entry.get_text().strip()
                if username and password:
                    self.message_label.set_text("Connecting...")
                    self.connecting = True
                    self.awaiting_login = True
                    self.login_thread = threading.Thread(target=self.background_login, args=(username, password))
                    self.login_thread.start()

            elif event.ui_element == self.register_button:
                if not hasattr(self, 'register_popup') or self.register_popup is None:
                    self.open_register_popup()

            elif self.forgot_password_button and event.ui_element == self.forgot_password_button:
                self.open_forgot_password_popup()

            if hasattr(self, 'register_popup') and event.ui_element == self.register_popup.cancel_button:
                self.register_popup.kill()

        if event.type == pygame_gui.UI_CONFIRMATION_DIALOG_CONFIRMED:
            if hasattr(self, 'register_popup') and event.ui_element == self.register_popup:
                username = self.register_username_entry.get_text().strip()
                password = self.register_password_entry.get_text().strip()
                email = self.register_email_entry.get_text().strip()

                if username and password and email:
                    success = attempt_register(username, password, email)
                    if success:
                        self.message_label.set_text("Registration Successful! Please login.")
                    else:
                        self.message_label.set_text("Registration Failed.")
                else:
                    self.message_label.set_text("All fields required.")

                self.register_popup.kill()

    def update(self, time_delta):
        self.manager.update(time_delta)

        if self.awaiting_login and self.login_thread and not self.login_thread.is_alive():
            self.awaiting_login = False
            self.connecting = False

            if self.login_result:
                self.screen_manager.auth_token = self.login_result
                self.screen_manager.current_account = self.username_entry.get_text().strip()
                self.message_label.set_text("Login successful!")
                character_select_screen_class = ScreenRegistry.get("character_select")
                if character_select_screen_class:
                    self.screen_manager.set_screen(character_select_screen_class(self.manager, self.screen_manager))
            else:
                self.message_label.set_text("Login Failed. Forgot password?")
                if not self.forgot_password_button_created:
                    self.forgot_password_button = pygame_gui.elements.UIButton(
                        relative_rect=pygame.Rect((250, 460), (300, 30)),
                        text="Forgot Password?",
                        manager=self.manager
                    )
                    self.forgot_password_button_created = True

    def draw(self, window_surface):
        self.manager.draw_ui(window_surface)

        self.register_popup = pygame_gui.windows.UIConfirmationDialog(
            rect=pygame.Rect((200, 200), (400, 300)),
            manager=self.manager,
            window_title="Register New Account",
            action_long_desc="Enter Username, Password, and Email.",
            object_id="#register_popup"
        )

        self.register_username_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((50, 100), (300, 30)),
            manager=self.manager,
            container=self.register_popup
        )
        self.register_password_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((50, 140), (300, 30)),
            manager=self.manager,
            container=self.register_popup
        )
        self.register_email_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((50, 180), (300, 30)),
            manager=self.manager,
            container=self.register_popup
        )

    def open_forgot_password_popup(self):
        # You can define forgot password popup if needed in future
        pass

# Add your helper functions for login/register here

def attempt_register(username, password, email):
    try:
        response = requests.post(
            f"{SERVER_URL}/register",
            json={"username": username, "password": password, "email": email}
        )

        return response.status_code == 200
    except Exception as e:
        print(f"❌ Could not connect to server: {e}")
        return False

def attempt_login(username, password):
    try:
        response = requests.post(
            f"{SERVER_URL}/token",
            data={"username": username, "password": password}
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        else:
            return None
    except Exception as e:
        print(f"❌ Could not connect to server: {e}")
        return None

ScreenRegistry.register("login", LoginScreen)