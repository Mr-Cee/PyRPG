import io
import shutil
import tempfile
import zipfile

from screen_manager import BaseScreen
from account_manager import AccountManager
from screen_registry import ScreenRegistry
import pygame_gui
import pygame
import os
import sys
import json
import requests
import threading

from settings import *  # or wherever your server runs



def attempt_login(username, password):
    try:
        response = requests.post(
            f"{SERVER_URL}/login",
            json={
                "username": username,
                "password": password,
                "client_version": CLIENT_VERSION
            }
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            role = data.get("role", "player")
            return {"data": {"token": token, "role": role}}
        else:
            return {"error": response.json().get("detail", "Unknown error.")}

    except Exception as e:
        return {"error": f"Could not connect to server: {e}"}

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
    def __init__(self, manager, screen_manager, logout_reason=None):
        super().__init__(manager, screen_manager)
        self.clicked_this_frame = False
        self.remember_me_checked = False
        self.logout_reason = logout_reason
        self.connecting = False
        self.login_thread = None
        self.login_result = None
        self.awaiting_login = False
        self.forgot_password_popup = None
        self.new_password_popup = None
        self.reset_target_username = None
        self.register_popup = None

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

        self.username_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((150, 180), (90, 30)),
            text="Username:",
            manager=self.manager
        )

        self.password_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((150, 250), (90, 30)),
            text="Password:",
            manager=self.manager
        )

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
            relative_rect=pygame.Rect((250, 410), (30, 30)),
            text='',
            manager=self.manager
        )

        self.remember_me_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((290, 410), (100, 30)),
            text='Remember Me',
            manager=self.manager
        )

        self.forgot_password_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((250, 490), (300, 30)),
            text="Forgot Password?",
            manager=self.manager
        )

        self.update_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((GAME_WIDTH - 160, GAME_HEIGHT - 60), (150, 40)),
            text="Update Client",
            manager=self.manager
        )

        self.version_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((GAME_WIDTH - 160, GAME_HEIGHT - 25), (150, 20)),
            text=f"Version: {CLIENT_VERSION}",
            manager=self.manager
        )

        if self.logout_reason:
            from pygame_gui.windows import UIMessageWindow
            self.MessageWindow = UIMessageWindow(
                rect=pygame.Rect((300, 200), (300, 150)),
                window_title="Disconnected",
                html_message=f"<b>{self.logout_reason}</b>",
                manager=self.manager,
                object_id="#Error_Window"
            )
            self.Message_Label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect((10, 10), (400, 30)),
                text=f"⚠ {self.logout_reason}",
                manager=self.manager,
                object_id="#error_label"
            )
        self.fetch_login_banner()

        self.load_remembered_login() #Make sure this is at the end of setup

    def fetch_login_banner(self):
        try:
            response = requests.get(f"{SERVER_URL}/login_banner")
            if response.ok:
                banner = response.json().get("message", "")
                self.banner_text = banner
                if banner:
                    self.banner_label = pygame_gui.elements.UILabel(
                        relative_rect=pygame.Rect((GAME_WIDTH-450, 60), (400, 400)),
                        text=banner,
                        manager=self.manager,
                        object_id="#login_banner"
                    )
                    self.patch_notes_btn = pygame_gui.elements.UIButton(
                        relative_rect=pygame.Rect((GAME_WIDTH - 160, GAME_HEIGHT - 105), (150, 40)),
                        text="Patch Notes",
                        manager=self.manager,
                        # object_id="#patch_notes"
                    )
        except Exception as e:
            print("Failed to load banner:", e)

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
        self.username_label.kill()
        self.password_label.kill()
        self.update_button.kill()
        self.version_label.kill()
        if hasattr(self, "Message_Label"):
            self.Message_Label.kill()
        if hasattr(self, "MessageWindow"):
            self.MessageWindow.kill()
        self.patch_notes_btn.kill()
        self.banner_label.kill()

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
        result = attempt_login(username, password)
        self.login_result = result

    def open_forgot_password_popup(self):
        if self.forgot_password_popup:
            self.forgot_password_popup.kill()

        self.forgot_password_popup = pygame_gui.windows.UIConfirmationDialog(
            rect=pygame.Rect((200, 200), (400, 200)),
            manager=self.manager,
            window_title="Forgot Password",
            action_long_desc="Enter your email in the input field below.",
            object_id="#forgot_password_popup"
        )

        self.forgot_email_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((50, 65), (300, 30)),
            text="Email:",
            manager=self.manager,
            container=self.forgot_password_popup
        )
        # Create a small text entry line inside the popup
        self.forgot_email_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((50, 95), (300, 30)),
            manager=self.manager,
            container=self.forgot_password_popup
        )

    def open_register_popup(self):
        if hasattr(self, 'register_popup') and self.register_popup:
            return  # Prevent multiple popups

        self.register_popup = pygame_gui.windows.UIConfirmationDialog(
            rect=pygame.Rect((200, 200), (400, 300)),
            manager=self.manager,
            window_title="Register New Account",
            action_long_desc="Enter Username, Password, and Email."
        )

        self.register_username_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((50, 35), (300, 30)),
            text="Username:",
            manager=self.manager,
            container=self.register_popup
        )
        self.register_username_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((50, 60), (300, 30)),
            manager=self.manager,
            container=self.register_popup
        )

        self.register_password_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((50, 95), (300, 30)),
            text="Password:",
            manager=self.manager,
            container=self.register_popup
        )
        self.register_password_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((50, 120), (300, 30)),
            manager=self.manager,
            container=self.register_popup
        )

        self.register_email_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((50, 155), (300, 30)),
            text="Email:",
            manager=self.manager,
            container=self.register_popup
        )
        self.register_email_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((50, 180), (300, 30)),
            manager=self.manager,
            container=self.register_popup
        )

        self.register_password_entry.set_text_hidden(True)

    def open_new_password_popup(self, username):
        if self.new_password_popup:
            self.new_password_popup.kill()

        self.reset_target_username = username

        self.new_password_popup = pygame_gui.windows.UIConfirmationDialog(
            rect=pygame.Rect((200, 200), (400, 250)),
            manager=self.manager,
            window_title="Reset Password",
            action_long_desc="Enter a new password.",
            object_id="#new_password_popup"
        )
        self.new_password_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((50, 60), (300, 30)),
            text="New Password:",
            manager=self.manager,
            container=self.new_password_popup
        )
        self.new_password_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((50, 90), (300, 30)),
            manager=self.manager,
            container=self.new_password_popup
        )



        self.new_password_confirm_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((50, 120), (300, 30)),
            text="Confirm Password:",
            manager=self.manager,
            container=self.new_password_popup
        )
        self.new_password_confirm_entry = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((50, 150), (300, 30)),
            manager=self.manager,
            container=self.new_password_popup
        )

    def show_popup(self, title, message):
        from pygame_gui.elements import UIWindow, UILabel, UIButton

        print(str(len(message)) + " " + message)

        # Estimate width from message length (basic heuristic)
        estimated_width = max(300, min(600, len(message) * 10))
        window_rect = pygame.Rect(
            (GAME_WIDTH // 2 - estimated_width // 2, GAME_HEIGHT // 2 - 75),
            (estimated_width, 175)
        )

        popup = UIWindow(
            window_rect,
            self.manager,
            window_display_title=title
        )

        UILabel(
            pygame.Rect((10, 30), (estimated_width - 20, 60)),
            message,
            self.manager,
            container=popup
        )

        UIButton(
            pygame.Rect(((estimated_width - 100) // 2, 100), (100, 30)),
            "OK",
            self.manager,
            container=popup
        )

        self.active_popup = popup

    def show_patch_notes_popup(self):
        try:
            response = requests.get(f"{SERVER_URL}/patch_notes", timeout=5)
            notes = response.json().get("notes", "No patch notes available.")
        except:
            notes = "Failed to load patch notes."

        from pygame_gui.windows import UIMessageWindow
        UIMessageWindow(
            rect=pygame.Rect((200, 150), (500, 400)),
            window_title="Patch Notes",
            html_message=f"<b>Patch Notes:</b><br><br>{notes.replace('\n', '<br>')}",
            manager=self.manager,
            object_id="#patch_notes"
        )

    def handle_event(self, event):

        if event.type == pygame.USEREVENT + 99 and getattr(self, "restart_pending", False):
            print("[Restart] Relaunching client...")
            python = sys.executable
            os.execl(python, python, *sys.argv)  # Relaunch the script using the same command

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

            if hasattr(self, "active_popup") and event.ui_element.text == "OK":
                self.active_popup.kill()
                self.active_popup = None

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

            if event.ui_element == self.login_button:
                #if self.account_manager.login(username, password):
                if username and password:
                    self.message_label.set_text("Connecting to server...")
                    self.connecting = True
                    self.awaiting_login = True

                    # Start the login attempt in a background thread
                    self.login_thread = threading.Thread(target=self.background_login, args=(username, password))
                    self.login_thread.start()
                else:
                    self.message_label.set_text("Username and password required.")

            if event.ui_element == self.register_button:
                self.open_register_popup()

            if hasattr(self, 'register_popup') and self.register_popup:
                if event.ui_element == self.register_popup.cancel_button:
                    self.register_popup.kill()
                    self.register_popup = None

            if self.forgot_password_popup and event.ui_element == self.forgot_password_popup.cancel_button:
                self.forgot_password_popup.kill()

            if self.new_password_popup and event.ui_element == self.new_password_popup.cancel_button:
                self.new_password_popup.kill()

            if event.ui_element == self.update_button:
                try:
                    version_response = requests.get(f"{SERVER_URL}/required_version", timeout=5)
                    if version_response.status_code == 200:
                        required = version_response.json()["version"]
                        if required != CLIENT_VERSION:
                            # Example GitHub release ZIP URL (customize for your project)
                            zip_url = version_response.json()["download_url"]
                            threading.Thread(target=self.download_and_apply_update, args=(zip_url, required)).start()
                        else:
                            self.show_popup("No Update Needed", "Client version already matches the server.")
                    else:
                        self.show_popup("Update Failed", "Could not fetch server version.")
                except requests.exceptions.RequestException:
                    self.show_popup("Connection Error", "Failed to connect to server.")

            if event.ui_element == getattr(self, "patch_notes_btn", None):
                self.show_patch_notes_popup()


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

            elif hasattr(self, 'register_popup') and event.ui_element == self.register_popup:
                username = self.register_username_entry.get_text().strip()
                password = self.register_password_entry.get_text().strip()
                email = self.register_email_entry.get_text().strip()

                if username and password and email:
                    if attempt_register(username, password, email):
                        self.message_label.set_text("Registration Successful! Please login.")
                    else:
                        self.message_label.set_text("Registration Failed.")
                else:
                    self.message_label.set_text("All fields required.")

                self.register_popup.kill()
                self.register_popup = None

    def update(self, time_delta):
        self.manager.update(time_delta)

        if self.awaiting_login and self.login_thread and not self.login_thread.is_alive():
            self.awaiting_login = False
            self.connecting = False

            if self.login_result:
                if "data" in self.login_result:
                    data = self.login_result["data"]
                    self.screen_manager.auth_token = data["token"]
                    self.screen_manager.player_role = data.get("role", "player")
                    self.screen_manager.current_account = self.username_entry.get_text().strip()
                    self.message_label.set_text("Login successful!")

                    if self.remember_me_checked:
                        self.save_remembered_login(self.screen_manager.current_account)
                    else:
                        self.clear_remembered_login()

                    character_select_screen_class = ScreenRegistry.get("character_select")
                    if character_select_screen_class:
                        self.screen_manager.set_screen(
                            character_select_screen_class(self.manager, self.screen_manager)
                        )

                elif "error" in self.login_result:
                    self.show_popup("Login Failed", self.login_result["error"])

    def draw(self, window_surface):
        self.manager.draw_ui(window_surface)

    def download_and_apply_update(self, zip_url, required_version):
        try:
            response = requests.get(zip_url, stream=True)
            response.raise_for_status()

            total_length = response.headers.get('content-length')
            if total_length is None:
                self.show_popup("Update Failed", "Could not determine update size.")
                return

            total_length = int(total_length)
            downloaded = 0
            buffer = io.BytesIO()

            for chunk in response.iter_content(chunk_size=4096):
                if chunk:
                    buffer.write(chunk)
                    downloaded += len(chunk)
                    percent = int(100 * downloaded / total_length)
                    self.message_label.set_text(f"Downloading... {percent}%")

            buffer.seek(0)
            safe_extract_and_apply(buffer, required_version)
            # with zipfile.ZipFile(buffer, 'r') as zip_ref:
            #     zip_ref.extractall(".")  # Extract into current directory

            # Update version in settings.py
            with open("settings.py", "r", encoding="utf-8") as f:
                lines = f.readlines()
            with open("settings.py", "w", encoding="utf-8") as f:
                for line in lines:
                    if line.startswith("CLIENT_VERSION"):
                        f.write(f'CLIENT_VERSION = "{required_version}"\n')
                    else:
                        f.write(line)

            self.show_popup("Update Complete", f"Updated to {required_version}. Restarting...")
            pygame.time.set_timer(pygame.USEREVENT + 99, 1500)
            self.restart_pending = True

        except Exception as e:
            self.show_popup("Update Failed", str(e))



def safe_extract_and_apply(buffer, required_version):
    temp_dir = tempfile.mkdtemp()

    with zipfile.ZipFile(buffer, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    # List of folders/files to skip (adjust as needed)
    skip = {".git", "__pycache__", "saves", "config.json"}

    for root, dirs, files in os.walk(temp_dir):
        rel_path = os.path.relpath(root, temp_dir)
        target_path = os.path.join(".", rel_path)

        # Skip excluded folders
        if any(part in skip for part in rel_path.split(os.sep)):
            continue

        os.makedirs(target_path, exist_ok=True)

        for file in files:
            src_file = os.path.join(root, file)
            dst_file = os.path.join(target_path, file)

            try:
                shutil.copy2(src_file, dst_file)
            except PermissionError:
                print(f"[Update] Skipped {dst_file} due to permission error.")

    shutil.rmtree(temp_dir)

# 🚀 Register this screen
ScreenRegistry.register("login", LoginScreen)