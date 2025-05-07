# chat_system.py
import inspect
import threading
import time
import requests
import pygame
import pygame_gui
import datetime

from screens.login_screen import LoginScreen
from pyexpat.errors import messages

from my_reports_window import MyReportsWindow
from player_registry import get_player
from reports_window import ReportsWindow
from settings import *

import items
from items import create_item


ROLE_HIERARCHY = {
    "player": 0,
    "gm": 1,
    "dev": 2
}

from settings import SERVER_URL

class ChatWindow:
    def __init__(self, manager, player, screen_manager, container=None, inventory_screen=None):
        self.player = player
        self.manager = manager
        self.screen_manager = screen_manager
        self.container = container
        self.inventory_screen = inventory_screen

        self.tabs = ["All", "Chat", "System", "Combat"]
        if self.player.role in ("gm", "dev"):
            self.tabs.append("Admin")
        self.active_tab = "All"

        self.flashing_tabs = set()
        self.flash_timer = 0.0
        self.flash_on = False
        self.flash_interval = 0.5

        self.messages = {tab: [] for tab in self.tabs}
        self.MAX_MESSAGE_LENGTH = 500

        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect((10, 480), (400, 220)),
            manager=self.manager,
            container=self.container
        )

        self.tab_buttons = []
        button_width = 60
        for idx, tab in enumerate(self.tabs):
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect((5 + idx * (button_width + 5), 5), (button_width, 30)),
                text=tab,
                manager=self.manager,
                container=self.panel
            )
            self.tab_buttons.append(btn)

        self.scroll_container = pygame_gui.elements.UIScrollingContainer(
            relative_rect=pygame.Rect((5, 40), (380, 130)),
            manager=self.manager,
            container=self.panel
        )

        self.labels = []
        self.y_offset = 5

        self.input_box = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((5, 175), (390, 30)),
            manager=self.manager,
            container=self.panel
        )
        self.input_box.hide()

        self.input_active = False
        self.defer_text = None
        self.history = []
        self.history_index = -1

        self.last_whisper_from = None

        # Command setup
        self.commands = {}
        self.commands.update(self._load_player_commands())
        self.commands.update(self._load_gm_commands())
        self.commands.update(self._load_dev_commands())
        self.admin_commands = ["broadcast", "kick", "mute", "unmute", "setbanner"]

        self.reports_window = None
        self.resolution_popup = None

        self.alias_map = {}
        for cmd_name, data in self.commands.items():
            for alias in data.get("aliases", []):
                self.alias_map[alias] = cmd_name

        self.fetch_recent_messages()

        self.running = True

        self.last_fetch_time = time.time()
        self.polling_thread = threading.Thread(target=self.poll_server_for_messages, daemon=True)
        self.polling_thread.start()

    def teardown(self):
        self.running = False
        self.panel.kill()
        for label in self.labels:
            label.kill()
        self.labels = []
        self.scroll_container.kill()
        self.input_box.kill()
        for btn in self.tab_buttons:
            btn.kill()

    def send_chat_to_server(self, text):
        payload = {
            "sender": self.player.name,
            "message": text,
            "timestamp": time.time(),
            "type": "Chat"
        }
        try:
            requests.post(f"{SERVER_URL}/chat/send", json=payload, timeout=1)
        except Exception as e:
            self.log_message(f"[Error] Failed to send message: {e}", "System")
            print(f"[Error] Failed to send message: {e}", "System")

    def poll_server_for_messages(self):
        while self.running:
            try:
                response = requests.get(
                    f"{SERVER_URL}/chat/fetch",
                    params={"since": self.last_fetch_time, "player_name": self.player.name},
                    timeout=2
                )

                if response.status_code == 200:
                    data = response.json()
                    for msg in data.get("messages", []):



                        self.last_fetch_time = max(self.last_fetch_time, msg["timestamp"])
                        msg_type = msg['type']
                        timestamp = msg["timestamp"]


                        if msg_type == "admin" and self.player.role not in ("gm", "dev"):
                            continue

                        elif msg_type == "whisper":
                            if msg['sender'] == self.player.name:
                                display = f"[To: {msg['recipient']}] {msg['message']}"
                            else:
                                display = f"[From: {msg['sender']}] {msg['message']}"
                                self.last_whisper_from = msg["sender"]
                            tab = "Chat"
                            label_type = "Whisper"  # Ensure purple formatting

                        elif msg_type == "InventoryUpdate":
                            if self.inventory_screen:
                                self.inventory_screen.reload_inventory()
                            continue

                        elif msg_type == "System" and msg.get("recipient") == self.player.name:
                            message_lower = msg["message"].lower()
                            if message_lower.startswith("[kick]"):
                                self.screen_manager.force_logout(reason="Kicked by an admin")
                                continue  # Do not display kick message

                        else:
                            if msg_type in ("admin", "Admin"):
                                display = f"[Admin] {msg['message']}"
                            elif msg_type in ("system", "System"):
                                display = f"[System] {msg['message']}"
                            else:
                                display = f"{msg['sender']}: {msg['message']}"

                            tab = msg_type
                            label_type = msg_type.capitalize()

                        valid_tabs = {"Chat", "System", "Combat", "Admin"}
                        tab = tab.capitalize() if tab.capitalize() in valid_tabs else "Chat"

                        self.messages[tab].append((timestamp, msg["message"], label_type))
                        self.messages["All"].append((timestamp, msg["message"], label_type))

                        # Always display in current tab (All, Chat, etc.)
                        self._create_label(display, label_type)
                        # Flash target tab if not actively viewed
                        if tab != self.active_tab:
                            self.flashing_tabs.add(tab)
            except:
                pass
            time.sleep(2)

    def fetch_recent_messages(self):
        try:
            response = requests.get(f"{SERVER_URL}/chat/recent", timeout=2)
            if response.status_code == 200:
                data = response.json()
                for msg in data.get("messages", []):
                    msg_type = msg["type"]
                    if msg_type.lower() in ("whisper", "system"):
                        continue  # ✅ Skip whispers & system for history

                    # ✅ Skip admin messages unless player has access
                    if msg_type.lower() == "admin" and self.player.role not in ("gm", "dev"):
                        continue

                    if msg_type not in self.messages:
                        continue  # Skip types we don't support

                    self.messages[msg_type].append((msg["timestamp"], msg["message"], msg_type))
                    self.messages["All"].append((msg["timestamp"], msg["message"], msg_type))

                    # display = f"{msg['sender']}: {msg['message']}" if msg_type == "Chat" else f"[{msg['timestamp']}] {msg['message']}"
                    if msg_type.lower() == "chat":
                        display = f"{msg['sender']}: {msg['message']}"
                    elif msg_type.lower() == "admin":
                        display = f"[Admin] {msg['message']}"
                    elif msg_type.lower() == "system":
                        display = f"[System] {msg['message']}"
                    else:
                        display = f"[{msg_type}] {msg['message']}"
                    if self.active_tab == msg_type or self.active_tab == "All":
                        self._create_label(display, msg_type)
        except Exception as e:
            self.log_message(f"[Error] Failed to load recent chat: {e}", "System")

    def _load_player_commands(self):
        return {
            "help": {
                "func": self.cmd_help,
                "min_role": "player",
                "aliases": [],
                "help": "Usage: /commands\nLists all available commands (no descriptions)."
            },
            "commands":{
                "func": self.cmd_commands,
                "min_role": "player",
                "aliases": [],
                "help": "Usage: /commands\nLists all available commands (no descriptions)."
            },
            "status": {
                "func": self.cmd_status,
                "min_role": "player",
                "aliases": [],
                "help": "Usage: /status\nShow your current role."
            },
            "online": {
                "func": self.cmd_online,
                "min_role": "player",
                "aliases": [],
                "help": "Usage: /online\nShow who's currently online."
            }

        }

    def _load_gm_commands(self):
        return {
            "admin": {
                "func": self.cmd_admin,
                "min_role": "gm",
                "aliases": [],
                "help": "Usage: /admin\nToggles admin mode (GM only)."
            },
            "reports-view": {
                "func": self.cmd_reports_view,
                "min_role": "gm",
                "help": "Shows all open report cases."
            },
            "report-resolve": {
                "func": self.cmd_report_resolve,
                "min_role": "gm",
                "help": "Usage: /report-resolve <case number>",
                "params": ["case_id"]
            },
            "stats": {
                "func": self.cmd_stats,
                "min_role": "gm",
                "aliases": [],
                "help": "Usage: /stats [player_name]\nView your stats or another player's."
            }
        }

    def _load_dev_commands(self):
        return {
            "addcoins": {
                "func": self.cmd_addcoins,
                "min_role": "dev",
                "aliases": ["ac"],
                "help": "Usage: /addcoins <amount> <type>\nAdds coins to player."
            },
            "createitem": {
                "description": "Create item: /createitem <slot_type> [char_class] [rarity] [weapon_type] [level] [target]",
                "roles": ["gm", "dev"],
                "func": self.cmd_createitem
            },
            "addExperience": {
                "func": self.cmd_addexperience,
                "min_role": "dev",
                "aliases": [""],
                "help": "Usage: /addExperience <amount> [player]\nGives experience to self if no player is specified."
            }
        }

    def send_admin_command(self, command_text):
        try:
            response = requests.post(
                f"{SERVER_URL}/admin_command",
                json={
                    "username": self.player.username,
                    "command": command_text
                },
                timeout=5
            )
            data = response.json()
            if data.get("success"):
                pass
                # # ✅ Send to server chat as an admin message
                # payload = {
                #     "sender": self.player.name,
                #     "message": data.get("message"),
                #     "timestamp": time.time(),
                #     "type": "Admin"
                # }
                # try:
                #     requests.post(f"{SERVER_URL}/chat/send", json=payload, timeout=2)
                # except Exception as e:
                #     self.log_message(f"[Error] Failed to log admin message: {e}", "System")
            else:
                self.log_message(f"[Error] {data.get('error')}", "System")
        except Exception as e:
            self.log_message(f"[Error] Admin command failed: {e}", "System")

    def wrap_text(self, text, font, max_width):
        if isinstance(text, tuple):
            text = text[0]

        wrapped_lines = []
        for paragraph in text.splitlines():
            line = ''
            for word in paragraph.split():
                if font.size(word)[0] > max_width:
                    broken = []
                    current = ''
                    for char in word:
                        if font.size(current + char)[0] <= max_width:
                            current += char
                        else:
                            broken.append(current)
                            current = char
                    if current:
                        broken.append(current)

                    for part in broken:
                        if line:
                            wrapped_lines.append(line)
                        line = part
                else:
                    test_line = f"{line} {word}".strip()
                    if font.size(test_line)[0] <= max_width:
                        line = test_line
                    else:
                        wrapped_lines.append(line)
                        line = word
            wrapped_lines.append(line)

        return wrapped_lines

    def log_message(self, message, msg_type="Chat"):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        if msg_type not in self.tabs:
            msg_type = "Chat"

        # Display with name prefix for Chat, timestamp otherwise
        if msg_type == "Chat":
            display_text = f"{self.player.name}: {message}"
        elif msg_type == "System":
            display_text = message  # No timestamp for System messages
        else:
            display_text = f"[{timestamp}] {message}"

        self.messages[msg_type].append((timestamp, message, msg_type))
        self.messages["All"].append((timestamp, message, msg_type))

        if self.active_tab == msg_type or self.active_tab == "All":
            self._create_label(display_text, msg_type)
        else:
            self.flashing_tabs.add(msg_type)

    def _create_label(self, text, msg_type="Chat"):
        object_id = f"#chat_message_{msg_type.lower()}"

        font = self.manager.get_theme().get_font([object_id])
        container_width = self.scroll_container.get_relative_rect().width
        label_width = container_width - 10

        if len(text) > self.MAX_MESSAGE_LENGTH:
            text = text[:self.MAX_MESSAGE_LENGTH - 3] + "..."

        wrapped_lines = self.wrap_text(text, font, label_width-20)

        for line in wrapped_lines:
            label = pygame_gui.elements.UILabel(
                relative_rect=pygame.Rect((5, self.y_offset), (label_width, 20)),
                text=line,
                manager=self.manager,
                container=self.scroll_container,
                object_id=object_id,
                anchors={"top": "top", "left": "left"}
            )
            self.labels.append(label)
            self.y_offset += 25

        self.scroll_container.set_scrollable_area_dimensions((label_width - 20, self.y_offset))
        self.scroll_container.vert_scroll_bar.set_scroll_from_start_percentage(100)

    def send_whisper(self, target_name, message):
        try:
            response = requests.post(
                f"{SERVER_URL}/whisper",
                json={
                    "sender": self.player.name,
                    "recipient": target_name,
                    "message": message
                },
                timeout=5
            )
            data = response.json()
            if data.get("success"):
                pass
                # display_text = f"[To: {target_name}] {message}"
                # timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                # self.messages["Chat"].append((timestamp, display_text, "Whisper"))
                # self.messages["All"].append((timestamp, display_text, "Whisper"))
                # if self.active_tab in ("All", "Chat"):
                #     self._create_label(display_text, "Whisper")
                # else:
                #     self.flashing_tabs.add("Chat")
            else:
                self.log_message(f"[System] {data.get('error', 'Failed to send whisper.')}", "System")
        except Exception as e:
            self.log_message(f"[Error] Whisper failed: {e}", "System")

    def switch_tab(self, new_tab):
        if new_tab not in self.tabs:
            return

        self.active_tab = new_tab
        self.flashing_tabs.discard(new_tab)

        for label in self.labels:
            label.kill()

        self.labels = []
        self.y_offset = 0

        self.scroll_container.kill()
        self.scroll_container = pygame_gui.elements.UIScrollingContainer(
            relative_rect=pygame.Rect((5, 40), (380, 130)),
            manager=self.manager,
            container=self.panel
        )

        for timestamp, message, msg_type in self.messages[new_tab] if new_tab != "All" else self.messages["All"]:
            if msg_type == "Chat":
                display_text = f"{self.player.name}: {message}"
            elif msg_type == "Whisper":
                display_text = message  # already formatted like [To: X] msg or [From: X] msg
            elif msg_type == "Admin":
                display_text = f"[Admin] {message}"
            elif msg_type == "System":
                display_text = f"[System] {message}"
            else:
                display_text = f"[{msg_type}] {message}"

            self._create_label(display_text, msg_type)


        self.scroll_container.rebuild()
        self.scroll_container.vert_scroll_bar.reset_scroll_position()
        self.scroll_container.vert_scroll_bar.set_scroll_from_start_percentage(100)

    def toggle_input(self):
        if self.input_active:
            self.input_box.hide()
            self.input_active = False
        else:
            self.input_box.show()
            self.input_box.focus()
            self.input_active = True
            self.input_box.set_text("")

    def process_event(self, event):

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SLASH):
                if not self.input_active:
                    self.toggle_input()
                    if event.key == pygame.K_SLASH:
                        self.defer_text = "/"
                else:
                    if event.key == pygame.K_RETURN:
                        text = self.input_box.get_text().strip()
                        self.history.append(text)
                        self.history_index = len(self.history)
                        if text:
                            if text.startswith("/"):
                                self.handle_command(text)
                            else:
                                self.send_chat_to_server(text)
                                # self.log_message(text, "Chat")

                        self.toggle_input()

            elif event.key == pygame.K_UP and self.input_active:
                if self.history and self.history_index > 0:
                    self.history_index -= 1
                    self.input_box.set_text(self.history[self.history_index])

            elif event.key == pygame.K_DOWN and self.input_active:
                if self.history and self.history_index < len(self.history) - 1:
                    self.history_index += 1
                    self.input_box.set_text(self.history[self.history_index])
                else:
                    self.input_box.set_text("")

        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            for idx, btn in enumerate(self.tab_buttons):
                if event.ui_element == btn:
                    self.switch_tab(self.tabs[idx])


        if self.reports_window:
            self.reports_window.process_event(event)

        if self.resolution_popup:
            if self.resolution_popup.process_event(event):
                return True

    def update(self, time_delta):
        if self.defer_text is not None and self.input_active:
            self.input_box.set_text(self.defer_text)
            self.input_box.focus()
            self.defer_text = None

        self.flash_timer += time_delta
        if self.flash_timer >= self.flash_interval:
            self.flash_timer = 0.0
            self.flash_on = not self.flash_on

            for idx, tab_name in enumerate(self.tabs):
                if tab_name in self.flashing_tabs:
                    button = self.tab_buttons[idx]
                    if self.flash_on:
                        button.select()
                    else:
                        button.unselect()


        # --- Command handling ---

    def has_permission(self, required_role):
        return ROLE_HIERARCHY.get(self.player.role, 0) >= ROLE_HIERARCHY.get(required_role, 0)

    def handle_command(self, user_input):
        parts = user_input[1:].split()
        command = parts[0].lower()
        args = parts[1:]

        if command == "help":
            if not args:
                self.log_message("[Help] Available commands:", "System")
                for cmd_name, cmd_data in self.commands.items():
                    min_role = cmd_data.get("min_role", "player")
                    if self.has_permission(min_role):
                        aliases = cmd_data.get("aliases", [])
                        alias_text = f" ({', '.join(aliases)})" if aliases else ""

                        help_line = cmd_data.get("help", "").split('\n')[0]  # just show first line
                        self.log_message(f"  /{cmd_name}{alias_text} - {help_line}", "System")
            else:
                help_target = args[0]
                if help_target in self.alias_map:
                    help_target = self.alias_map[help_target]
                min_role = self.commands[help_target].get("min_role", "player")
                if help_target in self.commands:
                    if self.has_permission(min_role):
                        help_line = self.commands[help_target].get("help")
                        self.log_message(f"{help_line}", "System")
            return

        elif command in ("tell", "t", "w"):
            if len(args) < 2:
                self.log_message("[System] Usage: /tell <playername> <message>", "System")
                return
            target = args[0]
            message = ' '.join(args[1:])
            self.send_whisper(target, message)
            return

        elif command in ("r", "reply"):
            if not self.last_whisper_from:
                self.log_message("[System] No one to reply to.", "System")
                return
            if not args:
                self.log_message("[System] Usage: /r <message>", "System")
                return
            self.send_whisper(self.last_whisper_from, ' '.join(args))
            return

        elif command == "gms":
            self.check_online_gms()
            return

        elif command == "staff":
            self.check_online_staff()
            return

        elif command == "report":
            self.send_report(" ".join(args))
            return

        elif command == "myreports":
            try:
                response = requests.get(f"{SERVER_URL}/my_reports", params={"player_name": self.player.name})
                reports = response.json()
                MyReportsWindow(self.manager, reports, self.player.name)
                return
            except Exception as e:
                self.log_message(f"[Error] Could not fetch your reports: {e}", "System")

        elif command in ("reports-view", "reports"):
            if self.player.role not in ("gm", "dev"):
                self.log_message("[System] You do not have permission to use this command.\nTry /report to generate a report or /myreports to see your reports", "System")
                return
            try:
                response = requests.get(f"{SERVER_URL}/reports_view")
                if response.status_code == 200:
                    reports = response.json().get("reports", [])
                    self.reports_window = ReportsWindow(self.manager, reports, self)
                else:
                    self.log_message("[Error] Failed to fetch reports from server.", "System")
            except Exception as e:
                self.log_message("[Error] Could not connect to server for reports.", "System")
                print(f"[Reports Error] {e}")
            return

        elif command == "createitem":
            min_role = "dev"
            if self.has_permission(min_role):
                self.cmd_createitem(*args)
            else:
                self.log_message("No Command Found", "System")

            return

        elif command == "addexperience":
            min_role = "dev"
            if self.has_permission(min_role):
                self.cmd_addexperience(*args)
                self.player.refresh_stats_and_level()

            else:
                self.log_message("No Command Found", "System")

            return

        elif command == "addcoins":
            min_role = "dev"
            if self.has_permission(min_role):
                self.cmd_addcoins(*args)

            else:
                self.log_message("No Command Found", "System")

            return

        elif command == "stats":
            min_role = "gm"
            if self.has_permission(min_role):
                self.cmd_stats(args)
            else:
                self.log_message("No Command Found", "System")
            return

        elif command in self.admin_commands:
            self.send_admin_command(f"/{command} {' '.join(args)}")
            return

        resolved_command = self.alias_map.get(command, command)

        if resolved_command in self.commands:
            command_entry = self.commands[resolved_command]
            min_role = command_entry.get("min_role", "player")
            if self.has_permission(min_role):
                func = command_entry["func"]
                try:
                    sig = inspect.signature(func)
                    params = [
                        p for p in sig.parameters.values()
                        if p.kind in (inspect.Parameter.POSITIONAL_ONLY,
                                      inspect.Parameter.POSITIONAL_OR_KEYWORD)
                    ]
                    required_params = [
                        p for p in params
                        if p.default == inspect.Parameter.empty
                    ]
                    param_names = [p.name for p in required_params]

                    try:
                        func(*args)
                    except TypeError as e:
                        self.log_message(f"[Error] Invalid usage of '{command}': {e}", "System")
                    except Exception as e:
                        self.log_message(f"[Error] Command failed: {e}", "System")


                except Exception as e:
                    self.log_message(f"[Error] Command failed: {e}", "System")
            else:
                self.log_message("No Command Found", "System")
        else:
            self.log_message("No Command Found", "System")
# --- Command functions ---
    def cmd_help(self, *args):
        self.log_message("[Help] Available commands:", "System")
        for cmd_name, cmd_data in self.commands.items():
            min_role = cmd_data.get("min_role", "player")
            aliases = cmd_data.get("aliases", [])
            alias_text = f" ({', '.join(aliases)})" if aliases else ""
            help_line = cmd_data.get("help", "").split('\n')[0]  # just show first line
            if self.has_permission(min_role):
                self.log_message(f"/{cmd_name}{alias_text} - {help_line}", "System")

    def cmd_commands(self):
        self.log_message("[Commands] Available:", "System")
        for cmd_name, cmd_data in self.commands.items():
            min_role = cmd_data.get("min_role", "player")
            if self.has_permission(min_role):
                self.log_message(f"/{cmd_name}", "System")

    def cmd_admin(self):
        self.log_message(f"[Admin] Your current role is: {self.player.role}", "System")

    def cmd_status(self):
        status_line = f"[Status] Your current role is: {self.player.role}"
        if getattr(self.player, "is_muted", False):
            status_line += " (Muted)"
        self.log_message(status_line, "System")

    def cmd_createitem(self, *args):
        if not args:
            self.log_message("Usage: /createitem type=head rarity=Rare level=5 target=PlayerName", "System")
            return

        # Abbreviation mapping
        key_map = {
            "t": "type",
            "rar": "rarity",
            "lvl": "level",
            "tgt": "target",
            "cls": "class",
            "wpn": "weapon_type"
        }

        # Convert args into a dictionary of key=value
        arg_str = " ".join(args)
        tokens = arg_str.split()
        kv_pairs = {}
        for token in tokens:
            if "=" in token:
                k, v = token.split("=", 1)
                k = k.lower()
                full_key = key_map.get(k, k)  # Expand abbreviation if present
                kv_pairs[full_key] = v

        if "type" not in kv_pairs:
            self.log_message("You must specify at least 'type=' for the item slot.", "System")
            return

        payload = {
            "slot_type": kv_pairs["type"],
            "char_class": kv_pairs.get("class", self.player.char_class or "Warrior"),
            "rarity": kv_pairs.get("rarity"),
            "item_level": int(kv_pairs.get("level", 1)),
            "weapon_type": kv_pairs.get("weapon_type"),
            "target": kv_pairs.get("target", self.player.name)
        }

        try:
            response = requests.post(f"{SERVER_URL}/createitem", json=payload, timeout=5)
            # response.raise_for_status()
            result = response.json()
            if result.get("success"):
                self.log_message(result.get("message"), "System")
                # Refresh inventory if item is for us
                if payload["target"] == self.player.name and self.inventory_screen:
                    self.inventory_screen.refresh_inventory_data()
            else:
                self.log_message(f"[Error] {result.get('error', 'Unknown error')}", "System")
        except Exception as e:
            self.log_message(f"[Error] Failed to contact server: {e}", "System")

    def cmd_addexperience(self, *args):
        if not args:
            self.log_message("[Usage] /addexperience <amount> [player]", "System")
            return

        try:
            amount = int(args[0])
        except ValueError:
            self.log_message("[Error] Amount must be a number.", "System")
            return

        target_name = args[1] if len(args) > 1 else self.player.name

        if target_name == self.player.name:
            # Local player
            self.player.gain_experience(amount)
            self.player.save_to_server(self.player.auth_token)
            self.log_message(f"[Dev] You gained {amount} experience!", "System")
            # Refresh inventory stat display if visible
            if self.inventory_screen and hasattr(self.inventory_screen, "refresh_stat_display"):
                self.inventory_screen.refresh_stat_display()
        else:
            try:
                response = requests.post(
                    f"{SERVER_URL}/add_experience",
                    json={
                        "requester": self.player.name,
                        "target": target_name,
                        "amount": amount
                    },
                    timeout=5
                )
                result = response.json()
                if result.get("success"):
                    self.log_message(f"[Dev] Gave {amount} XP to {target_name}.", "System")
                else:
                    self.log_message(f"[Error] {result.get('error')}", "System")
            except Exception as e:
                self.log_message(f"[Error] Failed to add experience: {e}", "System")

    def cmd_addcoins(self, *args):
        if len(args) < 2:
            self.log_message("[Usage] /addcoins <amount> <cointype> [player]", "System")
            return

        amount = args[0]
        coin_type = args[1]
        target = args[2] if len(args) > 2 else None

        payload = {
            "requester": self.player.username,
            "amount": amount,
            "coin_type": coin_type,
            "target": target
        }

        try:
            response = requests.post(f"{SERVER_URL}/add_coins", json=payload, timeout=5)
            result = response.json()
            if result.get("success"):
                self.log_message(f"[Coins] {result['message']}", "System")
                self.player.refresh_coins()
            else:
                self.log_message(f"[Error] {result.get('error', 'Unknown error')}", "System")
        except Exception as e:
            self.log_message(f"[Error] Failed to contact server: {e}", "System")

    def cmd_online(self):
        try:
            response = requests.get(f"{SERVER_URL}/online_players", timeout=2)
            data = response.json()
            players = data.get("online", [])
            if players:
                formatted = []
                for p in players:
                    name = p["name"]
                    if p.get("is_muted"):
                        name += " (Muted)"
                    formatted.append(name)
                self.log_message(f"[Online] {len(formatted)} player(s): {', '.join(formatted)}", "System")
            else:
                self.log_message("[Online] No players are currently online.", "System")
        except Exception as e:
            self.log_message(f"[Error] Failed to fetch online players: {e}", "System")

    def check_online_gms(self):
        try:
            response = requests.get(f"{SERVER_URL}/online_gms", timeout=5)

            data = response.json()

            if data.get("success"):
                gms = data.get("gms", [])
                if gms:
                    names = ", ".join(gms)
                    self.log_message(f"Online GMs: {names}", "System")
                else:
                    self.log_message("No GMs are currently online.", "System")
            else:
                self.log_message("[Error] Failed to fetch GM list.", "System")
        except Exception as e:
            self.log_message("[Error] Could not contact server.", "System")

    def check_online_staff(self):
        try:
            response = requests.get(f"{SERVER_URL}/online_staff", timeout=5)
            data = response.json()
            if data.get("success"):
                staff = data.get("staff", [])
                if staff:
                    listing = ", ".join(staff)
                    self.log_message(f"Online Staff: {listing}", "System")
                else:
                    self.log_message("No GMs or Devs are currently online.", "System")
            else:
                self.log_message("[Error] Failed to fetch staff list.", "System")
        except Exception as e:
            self.log_message("[Error] Could not contact server.", "System")

    def send_report(self, message):
        if not message:
            self.log_message("[Error] Usage: /report <your message>", "System")
            return
        try:
            response = requests.post(f"{SERVER_URL}/report", json={
                "sender": self.player.name,
                "message": message
            }, timeout=5)
            data = response.json()
            if data.get("success"):
                self.log_message("Your report has been sent to online staff.", "System")
            else:
                self.log_message(f"[Error] {data.get('error', 'Report failed.')}", "System")
        except Exception as e:
            self.log_message("[Error] Could not send report.", "System")

    def cmd_reports_view(self):
        try:
            res = requests.get(f"{SERVER_URL}/reports_view", timeout=5)
            data = res.json()
            if data.get("success"):
                for case in data.get("reports", []):
                    text = f"[Case #{case['id']}] {case['timestamp']} - {case['sender']}: {case['message']}"
                    self.log_message(text, "Admin")
            else:
                self.log_message("[Admin] Failed to load report log.", "System")
        except Exception:
            self.log_message("[Error] Could not reach server.", "System")

    def cmd_report_resolve(self, *args):
        if len(args) < 2:
            self.log_message("Usage: /report-resolve <case number> <resolution message>", "System")
            return

        try:
            case_id = int(args[0])
            resolution = " ".join(args[1:])
            res = requests.post(f"{SERVER_URL}/report_resolve", json={
                "case_id": case_id,
                "resolution": resolution
            }, timeout=5)
            data = res.json()
            if data.get("success"):
                self.log_message(f"✅ {data.get('message')}", "Admin")
            else:
                self.log_message(f"[Admin] {data.get('error')}", "System")
        except Exception:
            self.log_message("[Error] Could not contact server.", "System")

    def cmd_stats(self, *args):
        target = args[0] if args else self.player.name

        try:
            response = requests.get(
                f"{SERVER_URL}/player_stats",
                params={"requester_name": self.player.name, "target_name": target},
                timeout=5
            )
            if response.status_code != 200:
                self.log_message(f"[Stats] Could not fetch stats for {target}.", "System")
                return

            data = response.json()
            self.log_message(f"[Stats for {data['name']} - Level {data['level']} {data['char_class']}]", "System")
            coins = data.get("coins", {})

            formatted = f"{coins.get('platinum', 0)}p {coins.get('gold', 0)}g {coins.get('silver', 0)}s {coins.get('copper', 0)}c"
            self.log_message(f"Coins: {formatted}", "System")


            stats = data.get("total_stats", {})

            # Custom display order
            ordered_keys = [
                "Health",
                "Mana",
                "Strength",
                "Intelligence",
                "Dexterity",
                "Critical Chance",
                "Critical Damage",
                "Armor",
                "Avoidance",
                "Dodge",
                "Block"
            ]

            for key in ordered_keys:
                if key in stats:
                    self.log_message(f"{key}: {stats[key]}", "System")

            equipment = data.get("equipment", {})
            if equipment:
                self.log_message("Equipment:", "System")
                for slot, item in equipment.items():
                    if item:
                        self.log_message(f"  {slot}: {item.get('name', 'Unknown')}", "System")

        except Exception as e:
            self.log_message(f"[Error] Failed to fetch stats: {e}", "System")

    def parse_command_arguments(self, message: str):
        parts = message.split()
        args = {}
        for part in parts[1:]:
            if '=' in part:
                key, value = part.split('=', 1)
                args[key.strip()] = value.strip()
        return args

