from screen_manager import BaseScreen
from account_manager import AccountManager
from screen_registry import ScreenRegistry
import pygame_gui
import pygame
import os
import json
import requests
import threading

SERVER_URL = "http://localhost:8000"


def attempt_login(username, password):
    try:
        response = requests.post(
            f"{SERVER_URL}/login",
            data={"username": username, "password": password}
        )

        if response.status_code == 200:
            token = response.json().get("access_token")
            print(f"✅ Login successful! Token: {token}")
            return token
        else:
            print(f"❌ Login failed: {response.json()['detail']}")
            return None

    except Exception as e:
        print(f"❌ Could not connect to server: {e}")
        return None

def attempt_register(username, password, email):
    try:
        response = requests.post(
            f"{SERVER_URL}/register",
            json={"username": username, "password": password, "email": email}
        )

        if response.status_code == 200:
            print("✅ Registration successful!")
            return True
        else:
            print(f"❌ Registration failed: {response.json()['detail']}")
            return False

    except Exception as e:
        print(f"❌ Could not connect to server: {e}")
        return False

def attempt_forgot_password(email):
    try:
        response = requests.post(
            f"{SERVER_URL}/forgot-password",
            json={"email": email}
        )
        if response.status_code == 200:
            username = response.json().get("username")
            return username
        else:
            return None

    except Exception as e:
        print(f"❌ Could not connect to server: {e}")
        return None

def attempt_reset_password(username, new_password):
    try:
        response = requests.post(
            f"{SERVER_URL}/reset-password",
            json={"username": username, "new_password": new_password}
        )
        if response.status_code == 200:
            return True
        else:
            return False

    except Exception as e:
        print(f"❌ Could not connect to server: {e}")
        return False

class LoginScreen(BaseScreen):
    def __init__(self, manager, screen_manager):
        super().__init__(manager, screen_manager)
        self.clicked_this_frame = False
        self.remember_me_checked = False  # <<< Track checkbox state manually
        self.connecting = False
        self.login_thread = None
        self.login_result = None
        self.awaiting_login = False
        self.forgot_password_popup = None
        self.new_password_popup = None
        self.reset_target_username = None

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

        self.email_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((250, 310), (300, 50)),
            manager=self.manager
        )

        self.forgot_password_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((250, 460), (300, 30)),
            text="Forgot Password?",
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
        self.forgot_password_button.kill()
        self.email_entry.kill()

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

    def background_login(self, username, password):
        token = attempt_login(username, password)
        self.login_result = token

    def open_forgot_password_popup(self):
        if self.forgot_password_popup:
            self.forgot_password_popup.kill()

        self.forgot_password_popup = pygame_gui.windows.UIConfirmationDialog(
            rect=pygame.Rect((200, 200), (400, 200)),
            manager=self.manager,
            window_title="Forgot Password",
            action_long_desc="Enter your email in the input field below.",
            confirming_button_text="Submit",
            denying_button_text="Cancel",
            object_id="#forgot_password_popup"
        )

        # Create a small text entry line inside the popup
        self.forgot_email_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((50, 110), (300, 30)),
            manager=self.manager,
            container=self.forgot_password_popup
        )

    def open_new_password_popup(self, username):
        if self.new_password_popup:
            self.new_password_popup.kill()

        self.reset_target_username = username

        self.new_password_popup = pygame_gui.windows.UIConfirmationDialog(
            rect=pygame.Rect((200, 200), (400, 250)),
            manager=self.manager,
            window_title="Reset Password",
            action_long_desc="Enter a new password.",
            confirming_button_text="Reset",
            denying_button_text="Cancel",
            object_id="#new_password_popup"
        )

        self.new_password_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((50, 110), (300, 30)),
            manager=self.manager,
            container=self.new_password_popup
        )

        self.new_password_confirm_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((50, 150), (300, 30)),
            manager=self.manager,
            container=self.new_password_popup
        )

    def handle_event(self, event):

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                if self.username_entry.is_focused:
                    print("Test1")
                    self.username_entry.unfocus()
                    self.password_entry.focus()
                elif self.password_entry.is_focused:
                    print("test2")
                    self.password_entry.unfocus()
                    self.username_entry.focus()

            elif event.key == pygame.K_RETURN:
                username = self.username_entry.get_text().strip()
                password = self.password_entry.get_text().strip()
                if not username or not password:
                    self.message_label.set_text("Username and password required.")

                if username and password:
                    self.message_label.set_text("Connecting to server...")
                    self.connecting = True
                    self.awaiting_login = True

                    # Start the login attempt in a background thread
                    self.login_thread = threading.Thread(target=self.background_login, args=(username, password))
                    self.login_thread.start()

        elif event.type == pygame_gui.UI_BUTTON_PRESSED:

            if event.ui_element == self.forgot_password_button:
                self.open_forgot_password_popup()

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
            email = self.email_entry.get_text().strip()

            if not username or not password:
                self.message_label.set_text("Username and password required.")

            elif event.ui_element == self.login_button:
                #if self.account_manager.login(username, password):
                if username and password:
                    self.message_label.set_text("Connecting to server...")
                    self.connecting = True
                    self.awaiting_login = True

                    # Start the login attempt in a background thread
                    self.login_thread = threading.Thread(target=self.background_login, args=(username, password))
                    self.login_thread.start()

            elif event.ui_element == self.register_button:
                if username and password:
                    self.message_label.set_text("Connecting...")
                    self.connecting = True
                    success = attempt_register(username, password, email)
                    self.connecting = False

                    if success:
                        self.message_label.set_text("Registration Successful! Please login.")
                    else:
                        self.message_label.set_text("Registration Failed.")

            elif self.forgot_password_popup and event.ui_element == self.forgot_password_popup.cancel_button:
                self.forgot_password_popup.kill()

            elif self.new_password_popup and event.ui_element == self.new_password_popup.cancel_button:
                self.new_password_popup.kill()

        elif event.type == pygame_gui.UI_CONFIRMATION_DIALOG_CONFIRMED:
            if event.ui_element == self.forgot_password_popup:
                email = self.forgot_email_entry.get_text().strip()
                username = attempt_forgot_password(email)
                if username:
                    print(f"✅ Email found, resetting password for {username}")
                    self.open_new_password_popup(username)
                else:
                    self.message_label.set_text("Email not found.")
                self.forgot_password_popup.kill()

            elif event.ui_element == self.new_password_popup:
                new_password = self.new_password_entry.get_text().strip()
                confirm_password = self.new_password_confirm_entry.get_text().strip()

                if new_password != confirm_password:
                    self.message_label.set_text("Passwords do not match.")
                    return

                if attempt_reset_password(self.reset_target_username, new_password):
                    self.message_label.set_text("Password reset successful!")
                else:
                    self.message_label.set_text("Failed to reset password.")

                self.new_password_popup.kill()



    def update(self, time_delta):
        self.manager.update(time_delta)

        if self.awaiting_login and self.login_thread and not self.login_thread.is_alive():
            self.awaiting_login = False
            self.connecting = False

            if self.login_result:
                self.screen_manager.auth_token = self.login_result
                self.screen_manager.current_account = self.username_entry.get_text().strip()
                self.message_label.set_text("Login successful!")

                if self.remember_me_checked:
                    self.save_remembered_login(self.screen_manager.current_account)
                else:
                    self.clear_remembered_login()

                character_select_screen_class = ScreenRegistry.get("character_select")
                if character_select_screen_class:
                    self.screen_manager.set_screen(
                        character_select_screen_class(self.manager, self.screen_manager))
            else:
                self.message_label.set_text("Login Failed.")

    def draw(self, window_surface):
        self.manager.draw_ui(window_surface)

# 🚀 Register this screen
ScreenRegistry.register("login", LoginScreen)