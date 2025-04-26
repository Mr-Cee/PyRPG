import pygame
import pygame_gui
from pygame_gui.elements import UILabel, UIScrollingContainer
#from configuration import *
from pygame import freetype
from textwrap import wrap

pygame.init()

class ChatWindow:
    def __init__(self, screen,  manager, rect, object_ids=None):
        self.screen = screen
        self.manager = manager
        self.rect = rect
        self.object_ids = object_ids or {
            "system": "#chat_message_system",
            "chat": "#chat_message_chat",
            "combat": "#chat_message_combat",
            "admin": "#chat_message_admin",
            "debug": "#chat_message_debug"
        }

        self.tabs = {
            "All": [],
            "System": [],
            "Chat": [],
            "Combat": [],
            "Admin": [],
            "Debug": []
        }
        self.active_tab = "All"


        self.font = pygame.freetype.Font('./Assets/Fonts/EBGaramond-Regular.ttf',18)

        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect(rect.x, rect.y + 30, rect.width, rect.height - 30),
            manager=manager
        )

        self.container = pygame_gui.elements.UIScrollingContainer(
            relative_rect=pygame.Rect((0, 0), (rect.width, rect.height - 30)),  # <<< corrected here
            manager=self.manager,
            container=self.panel,
            anchors={"top": "top", "left": "left"}
        )

        self.tab_buttons = {}

        tab_names = ["All", "System", "Chat", "Combat", "Admin"]
        tab_width = 80
        tab_height = 25
        tab_spacing = 5
        start_x = 5

        for i, tab_name in enumerate(tab_names):
            button = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect((start_x + i * (tab_width + tab_spacing), rect.y, tab_width, tab_height)),
                text=tab_name,
                manager=self.manager
            )
            self.tab_buttons[tab_name] = button


        self.scroll_bar = self.container.vert_scroll_bar

        self.messages = []
        self.labels = []
        self.y_offset = 0
        self.MAX_MESSAGES = 100
        self.MAX_MESSAGE_LENGTH = 500
        self.auto_scroll_enabled = True

        # Flashing tab variables
        self.tabs_to_flash = set()
        self.flash_timer = 0.0
        self.flash_on = False
        self.flash_interval = 0.5  # seconds between flashes

    def wrap_text(self, text, font, max_width):
        if isinstance(text, tuple):
            text = text[0]
            print(text)

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
        #return "\n".join(wrapped_lines)
        return wrapped_lines

    def _create_label(self, text, msg_type="chat"):
        object_id = self.object_ids.get(msg_type, "#chat_message_chat")
        font = self.manager.get_theme().get_font([object_id])
        label_width = self.rect.width - 20
        # Protection against 500+ character messages
        if len(text) > self.MAX_MESSAGE_LENGTH:
            text = text[:self.MAX_MESSAGE_LENGTH - 3] + "..."

        wrapped_text = self.wrap_text(text, font, label_width)

        for wraptext in wrapped_text:
            temp_rect = self.font.render_to(self.screen, (-9999, -9999), wraptext, BLACK)
            temp_rect_height = temp_rect.height + 7

            # temp label to calculate height
            temp_label = UILabel(
                relative_rect=pygame.Rect((-9999, -9999), (label_width, 100)),
                text=wraptext,
                container=self.container,
                manager=self.manager,
                object_id=object_id,
                anchors={"top": "top", "left": "left"}
            )

            pygame.event.pump()
            self.manager.update(0)
            height = temp_rect_height

            temp_label.kill()

            # Real Label
            label = UILabel(
                relative_rect=pygame.Rect((0, self.y_offset), (label_width, height)),
                text=wraptext,
                container=self.container,
                manager=self.manager,
                object_id=object_id,
                anchors={"top": "top", "left": "left"}
            )

            self.labels.append(label)
            self.messages.append((text, msg_type))
            self.y_offset += height

        # Step 3: Remove oldest if too many
        if len(self.labels) > self.MAX_MESSAGES:
            oldest_label = self.labels.pop(0)
            oldest_message = self.messages.pop(0)
            self.y_offset -= oldest_label.rect.height
            oldest_label.kill()

            # Recalculate y_offsets for remaining messages
            current_y = 0
            for label in self.labels:
                label.set_relative_position((0, current_y))
                current_y += label.rect.height
            self.y_offset = current_y

        # Step 4: Resize scroll container's content area
        self.container.set_scrollable_area_dimensions((self.rect.width - 20, self.y_offset + 20))  # +20 bottom padding

        if self.auto_scroll_enabled:
            scroll_bar = self.container.vert_scroll_bar
            if scroll_bar:
                scroll_bar.set_scroll_from_start_percentage(100)

    def log_message(self, text, msg_type="chat", save=True):
        if save:
            self.messages.append((text, msg_type))
            self.tabs["All"].append((text, msg_type))
            if msg_type == "system":
                self.tabs["System"].append((text, msg_type))
            elif msg_type == "chat":
                self.tabs["Chat"].append((text, msg_type))
            elif msg_type == "combat":
                self.tabs["Combat"].append((text, msg_type))
            elif msg_type == "admin":
                self.tabs["Admin"].append((text, msg_type))
            elif msg_type == "debug":
                self.tabs["Debug"].append((text, msg_type))

            # 🚨 Only display if it belongs to the current tab
            if self.active_tab == "All" or self.active_tab.lower() == msg_type.lower():
                self._create_label(text, msg_type)

            # 🚨 Start flashing if message belongs to another tab
            tab_to_flash = None
            if msg_type == "system":
                tab_to_flash = "System"
            elif msg_type == "chat":
                tab_to_flash = "Chat"
            elif msg_type == "combat":
                tab_to_flash = "Combat"
            elif msg_type == "admin":
                tab_to_flash = "Admin"

            if tab_to_flash and tab_to_flash != self.active_tab:
                self.tabs_to_flash.add(tab_to_flash)

    def reload_messages(self):
        # Re-create all labels from saved messages
        self.labels = []
        self.y_offset = 0
        for text, msg_type in self.messages:
            self.log_message(text, msg_type)

    def reload_tab_messages(self):
        # Clear all labels safely
        for label in self.labels:
            if hasattr(label, 'label'):
                label.label.kill()
            else:
                label.kill()
        self.labels.clear()
        self.y_offset = 0

        # Load only messages from the selected tab
        for text, msg_type in self.tabs[self.active_tab]:
            self._create_label(text, msg_type)  # <<< call _create_label directly (not log_message)

        self.container.set_scrollable_area_dimensions((self.rect.width - 20, self.y_offset + 20))

        # Update tab highlights
        for tab_name, button in self.tab_buttons.items():
            if tab_name == self.active_tab:
                button.select()
            else:
                button.unselect()

    def process_events(self, event, save=False):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F1:
                self.active_tab = "All"
                self.reload_tab_messages()
            elif event.key == pygame.K_F2:
                self.active_tab = "System"
                self.reload_tab_messages()
            elif event.key == pygame.K_F3:
                self.active_tab = "Chat"
                self.reload_tab_messages()
            elif event.key == pygame.K_F4:
                self.active_tab = "Combat"
                self.reload_tab_messages()
            elif event.key == pygame.K_F5:
                self.active_tab = "Admin"
                self.reload_tab_messages()

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            for tab_name, button in self.tab_buttons.items():
                if event.ui_element == button:
                    self.active_tab = tab_name
                    self.reload_tab_messages()
                    # 🚨 Clear flashing on this tab
                    if tab_name in self.tabs_to_flash:
                        self.tabs_to_flash.remove(tab_name)
                        button.unselect()  # Make sure it's back to normal immediately

    def update(self, time_delta):
        # Update flashing timer
        self.flash_timer += time_delta

        if self.flash_timer >= self.flash_interval:
            self.flash_timer = 0.0
            self.flash_on = not self.flash_on

            for tab_name in self.tabs_to_flash:
                button = self.tab_buttons.get(tab_name)
                if button:
                    if self.flash_on:
                        button.select()  # Highlight
                    else:
                        button.unselect()  # Unhighlight
