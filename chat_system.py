# chat_system.py

import pygame
import pygame_gui
import datetime

# --- ChatWindow ---

class ChatWindow:
    def __init__(self, manager, container=None):
        self.manager = manager
        self.container = container

        # Chat tabs
        self.tabs = ["Chat", "System", "Combat", "Admin", "Debug"]
        self.active_tab = "Chat"

        # Flashing tabs notification
        self.flashing_tabs = set()

        # Store messages {tab: [(timestamp, text)]}
        self.messages = {tab: [] for tab in self.tabs}

        # Panel
        self.panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect((10, 300), (400, 250)),
            manager=self.manager,
            container=self.container
        )

        # Tabs (as buttons)
        self.tab_buttons = []
        button_width = 70
        for idx, tab in enumerate(self.tabs):
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect((5 + idx * (button_width + 5), 5), (button_width, 30)),
                text=tab,
                manager=self.manager,
                container=self.panel
            )
            self.tab_buttons.append(btn)

        # Chat container
        self.chat_container = pygame_gui.elements.UIScrollingContainer(
            relative_rect=pygame.Rect((5, 40), (390, 200)),
            manager=self.manager,
            container=self.panel
        )

        self.labels = []
        self.y_offset = 5

    def log_message(self, message, msg_type="Chat"):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        if msg_type not in self.messages:
            msg_type = "Chat"

        self.messages[msg_type].append((timestamp, message))

        # If message is for current tab, add label
        if msg_type == self.active_tab:
            self._add_label(timestamp, message)
        else:
            self.flashing_tabs.add(msg_type)

    def _add_label(self, timestamp, message):
        full_message = f"[{timestamp}] {message}"

        label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((5, self.y_offset), (380, 20)),
            text=full_message,
            manager=self.manager,
            container=self.chat_container
        )
        self.labels.append(label)
        self.y_offset += 25

        self.chat_container.set_scrollable_area_dimensions((390, self.y_offset + 5))
        self.chat_container.set_vertical_scroll_percentage(1.0)

    def switch_tab(self, new_tab):
        if new_tab not in self.tabs:
            return

        self.active_tab = new_tab
        self.flashing_tabs.discard(new_tab)

        for label in self.labels:
            label.kill()

        self.labels = []
        self.y_offset = 5

        for timestamp, message in self.messages[new_tab]:
            self._add_label(timestamp, message)

    def process_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            for idx, btn in enumerate(self.tab_buttons):
                if event.ui_element == btn:
                    self.switch_tab(self.tabs[idx])

    def update(self, time_delta):
        pass

# --- ChatInputBar ---

class ChatInputBar:
    def __init__(self, manager, chat_window, container=None):
        self.manager = manager
        self.chat_window = chat_window
        self.container = container

        self.input_active = False
        self.history = []
        self.history_index = -1

        # Input bar
        self.input_box = pygame_gui.elements.UITextEntryLine(
            relative_rect=pygame.Rect((10, 560), (400, 30)),
            manager=self.manager,
            container=self.container
        )
        self.input_box.hide()

    def toggle_input(self):
        if self.input_active:
            self.input_box.hide()
            self.input_active = False
        else:
            self.input_box.show()
            self.input_active = True
            self.input_box.set_text("")

    def process_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN and self.input_active:
                text = self.input_box.get_text().strip()
                if text:
                    self.chat_window.log_message(text, "Chat")
                    self.history.append(text)
                    self.history_index = len(self.history)
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
        pass
