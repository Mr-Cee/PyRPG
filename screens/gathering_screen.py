import pygame
import pygame_gui
from pygame import Rect
from pygame_gui.elements import UIButton, UILabel, UIPanel
import requests
import datetime

from chat_system import ChatWindow
from screen_manager import BaseScreen
from screen_registry import ScreenRegistry
from settings import SERVER_URL


class GatheringScreen(BaseScreen):
    def __init__(self, manager, screen_manager):
        super().__init__(manager, screen_manager)
        self.player = self.screen_manager.player
        self.manager = manager



        self.status_label = None
        self.level_labels = []
        self.buttons = []
        self.status_panel = None

        self.setup_ui()
        self.refresh_status()

    def setup(self):
        self.player.chat_window = ChatWindow(self.manager, self.player, self.screen_manager)
        self.player.chat_window.panel.set_relative_position((10, 480))
        self.player.chat_window.panel.set_dimensions((400, 220))

    def setup_ui(self):
        # Back button
        self.back_button = UIButton(
            relative_rect=Rect((10, 10), (100, 30)),
            text="Back",
            manager=self.manager
        )

        # Title
        self.title_label = UILabel(
            relative_rect=Rect((150, 10), (300, 30)),
            text="Gathering Activities",
            manager=self.manager
        )

        # Activity buttons
        activities = ["woodcutting", "mining", "farming", "scavenging"]
        for i, activity in enumerate(activities):
            btn = UIButton(
                relative_rect=Rect((100, 60 + i * 60), (200, 40)),
                text=activity.title(),
                manager=self.manager
            )
            btn.activity_name = activity
            self.buttons.append(btn)

        # Status panel
        self.status_panel = UIPanel(
            relative_rect=Rect((320, 60), (300, 180)),
            manager=self.manager
        )
        self.status_label = UILabel(
            relative_rect=Rect((10, 10), (280, 30)),
            text="Loading status...",
            manager=self.manager,
            container=self.status_panel
        )

        self.collect_button = UIButton(
            relative_rect=Rect((10, 100), (150, 30)),
            text="Collect Materials",
            manager=self.manager,
            container=self.status_panel
        )
        self.collect_button.hide()
        self.collect_button.disable()

        # Skill level labels
        levels = {
            "Woodcutting": self.player.woodcutting_level,
            "Mining": self.player.mining_level,
            "Farming": self.player.farming_level,
            "Scavenging": self.player.scavenging_level
        }
        for i, (skill, lvl) in enumerate(levels.items()):
            lbl = UILabel(
                relative_rect=Rect((10, 280 + i * 30), (300, 25)),
                text=f"{skill} Level: {lvl}",
                manager=self.manager
            )
            self.level_labels.append(lbl)



    def refresh_status(self):
        import threading, requests

        def fetch():
            try:
                response = requests.get(f"{SERVER_URL}/gather/state", params={"player_name": self.player.name})
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success"):
                        status_text = data.get("status", "")
                        self.status_label.set_text(status_text)

                        is_gathering = "Currently" in status_text
                        self.collect_button.show() if is_gathering else self.collect_button.hide()
                        self.collect_button.enable() if is_gathering else self.collect_button.disable()

                        print(status_text)
            except Exception as e:
                print("[Gathering] Failed to fetch state:", e)
        threading.Thread(target=fetch, daemon=True).start()

    def fetch_status(self):
        def worker():
            try:
                response = requests.post(
                    f"{SERVER_URL}/gather/status",
                    json={"player_name": self.player.name, "stop": False},
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("message") or data.get("error", "Unknown status.")
                    pygame.event.post(pygame.event.Event(pygame.USEREVENT, {"status_message": status}))
                else:
                    raise Exception("Failed status request")
            except Exception as e:
                pygame.event.post(pygame.event.Event(pygame.USEREVENT, {"status_message": "Status unavailable."}))

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def start_gathering(self, activity):
        def worker():
            try:
                response = requests.post(
                    f"{SERVER_URL}/gather/start",
                    json={"player_name": self.player.name, "activity": activity},
                    timeout=5
                )
                self.refresh_status()
            except Exception as e:
                print("[Gathering] Failed to start", e)

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def stop_gathering(self):
        def worker():
            try:
                response = requests.post(
                    f"{SERVER_URL}/gather/status",
                    json={"player_name": self.player.name, "stop": True},
                    timeout=5
                )
                self.fetch_status()
            except Exception as e:
                print("[Gathering] Failed to stop", e)

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def collect_materials_and_stop(self):
        def worker():
            try:
                response = requests.post(
                    f"{SERVER_URL}/collect_materials",
                    json={"player_name": self.player.name},
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    msg = data.get("message", "Collected.")
                    self.player.chat_window.log_message(msg, "System")
                else:
                    raise Exception("Collection failed.")
            except Exception as e:
                print( {"status_message": "Collection failed."})
            self.refresh_status()

        import threading
        threading.Thread(target=worker, daemon=True).start()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                from screens.main_game_screen import MainGameScreen
                self.screen_manager.set_screen(MainGameScreen(self.manager, self.screen_manager))
            elif event.ui_element == self.collect_button:
                self.collect_materials_and_stop()
            else:
                for btn in self.buttons:
                    if event.ui_element == btn:
                        self.start_gathering(btn.activity_name)
                        self.refresh_status()

        elif event.type == pygame.USEREVENT:
            if "status_message" in event.__dict__:
                self.status_label.set_text(event.status_message)

        # Let the chat system process any events too
        if self.player.chat_window:
            self.player.chat_window.process_event(event)

    def update(self, time_delta):
        self.manager.update(time_delta)

        if self.player.chat_window:
            self.player.chat_window.update(time_delta)

    def draw(self, surface):
        self.manager.draw_ui(surface)

    def teardown(self):
        self.back_button.kill()
        self.title_label.kill()
        self.status_label.kill()
        self.collect_button.kill()
        self.status_panel.kill()
        for btn in self.buttons:
            btn.kill()
        for lbl in self.level_labels:
            lbl.kill()
        if self.player.chat_window:
            print("Teardown")
            self.player.chat_window.teardown()
            self.player.chat_window = None
            print(self.player.chat_window)


ScreenRegistry.register("gathering", GatheringScreen)
