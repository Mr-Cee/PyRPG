# chat_system.py
import inspect
import threading
import time
import requests
import pygame
import pygame_gui
import datetime
from player_registry import get_player
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
    def __init__(self, manager, player, container=None):
        self.player = player
        self.manager = manager
        self.container = container

        self.tabs = ["All", "Chat", "System", "Combat", "Admin", "Debug"]
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

        # Command setup
        self.commands = {}
        self.commands.update(self._load_player_commands())
        self.commands.update(self._load_gm_commands())
        self.commands.update(self._load_dev_commands())
        self.admin_commands = ["broadcast", "kick", "mute", "unmute", "addcoins", "createitem"]

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

                        if msg_type == "whisper":
                            if msg['sender'] == self.player.name:
                                display = f"[To: {msg['recipient']}] {msg['message']}"
                            else:
                                display = f"[From: {msg['sender']}] {msg['message']}"
                            tab = "Chat"  # or use a separate "Whispers" tab if you want
                        else:
                            display = f"{msg['sender']}: {msg['message']}"
                            tab = msg_type

                        self.messages[tab].append((timestamp, msg["message"], msg_type))
                        self.messages["All"].append((timestamp, msg["message"], msg_type))

                        if self.active_tab == tab or self.active_tab == "All":
                            self._create_label(display, msg_type)
                        else:
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
                    if msg_type == "whisper" or "system":
                        continue  # ✅ Skip whispers entirely in recent load

                    # Insert into local memory
                    self.messages[msg["type"]].append((msg["timestamp"], msg["message"], msg_type))
                    self.messages["All"].append((msg["timestamp"], msg["message"], msg_type))

                    # Also display if it matches active tab
                    display = f"{msg['sender']}: {msg['message']}" if msg_type == "Chat" else f"[{msg['timestamp']}] {msg['message']}"
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
                "func": self.cmd_createitem,
                "min_role": "dev",
                "aliases": ["ci"],
                "help": "Usage: /createitem <slot_type> [char_class] [rarity] [player_name]\nCreates an item and gives it to a player."
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
                self.log_message(f"[Admin] {data.get('message')}", "System")
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
        display_text = f"{self.player.name}: {message}" if msg_type == "Chat" else f"[{timestamp}] {message}"

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

        self.scroll_container.set_scrollable_area_dimensions((label_width - 20, self.y_offset + 5))
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
                # self.log_message(f"[To {target_name}] {message}", "Whisper")
                pass
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
        self.y_offset = 5

        for timestamp, message, msg_type in self.messages[new_tab] if new_tab != "All" else self.messages["All"]:
            display_text = f"{self.player.name}: {message}" if msg_type == "Chat" else f"[{timestamp}] {message}"
            self._create_label(display_text, msg_type)

        self.scroll_container.set_scrollable_area_dimensions((self.scroll_container.get_relative_rect().width - 30, self.y_offset + 5))
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
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            for idx, btn in enumerate(self.tab_buttons):
                if event.ui_element == btn:
                    self.switch_tab(self.tabs[idx])

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

        elif command == "w" and len(args) >= 2:
            target_name = args[0]
            message = ' '.join(args[1:])
            self.send_whisper(target_name, message)
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

                    if len(args) < len(required_params):
                        self.log_message(f"[Error] Too few arguments for '{command}'.", "System")
                        self.log_message(f"Required: {', '.join(param_names)}", "System")
                    elif len(args) > len(params):
                        self.log_message(
                            f"[Error] Too many arguments for '{command}'. Max allowed: {len(params)}.\nUse /help {command} for more information",
                            "System")
                    else:
                        func(*args)
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
        self.log_message(f"[Status] Your current role is: {self.player.role}", "System")

    def cmd_addcoins(self, amount, cointype):
        try:
            amount = int(amount)
            if hasattr(self.player, "add_coins"):
                print("made it here")
                self.player.add_coins(amount, cointype)
                self.log_message(f"[Admin] Added {amount} {cointype} coins.", "System")
            else:
                print("here instead")
                self.log_message("[Debug] Player object has no 'add_coins' method.", "Debug")
        except ValueError:
            print("error")
            self.log_message("[Error] Invalid amount.", "System")

    def cmd_createitem(self, slot_type, char_class=None, rarity=None, target_player_name=None):
        target = self.player
        if target_player_name:
            target_lookup = get_player(target_player_name)
            if not target_lookup:
                self.log_message(f"[Dev] Player '{target_player_name}' not found.", "Debug")
                return
            target = target_lookup

        char_class = char_class or target.char_class
        item = create_item(slot_type=slot_type, char_class=char_class, rarity=rarity)

        success = target.add_to_inventory(item)
        if success:
            if target is self.player:
                self.log_message(f"[Dev] Created {item['rarity']} {slot_type.title()} for yourself.", "Debug")
            else:
                self.log_message(f"[Dev] Created {item['rarity']} {slot_type.title()} for {target.name}.", "Debug")
        else:
            self.log_message(f"[Dev] Failed to add item to {target.name}'s inventory (Full?).", "Debug")

    def cmd_online(self):
        try:
            response = requests.get(f"{SERVER_URL}/online_players", timeout=2)
            data = response.json()
            names = data.get("online", [])
            if names:
                self.log_message(f"[Online] {len(names)} player(s): {', '.join(names)}", "System")
            else:
                self.log_message("[Online] No players are currently online.", "System")
        except Exception as e:
            self.log_message(f"[Error] Failed to fetch online players: {e}", "System")

    def check_online_gms(self):
        try:
            response = requests.get(f"{SERVER_URL}/online_gms", timeout=5)
            print(response.text)
            data = response.json()
            print(data)
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





