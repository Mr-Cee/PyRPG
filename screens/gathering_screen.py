import pygame
import pygame_gui
from pygame import Rect
from pygame_gui.elements import UIButton, UILabel, UIPanel
import requests
import datetime
from screen_manager import BaseScreen
from screen_registry import ScreenRegistry
from settings import SERVER_URL


class GatheringScreen(BaseScreen):
    def __init__(self, manager, screen_manager):
        super().__init__(manager, screen_manager)
        self.player = screen_manager.player
        self.status_label = None
        self.level_labels = []
        self.buttons = []
        self.status_panel = None
        self.setup_ui()
        # self.fetch_status()
        self.refresh_status()

    def setup_ui(self):
        # Back button
        self.back_button = UIButton(
            relative_rect=Rect((10, 10), (100, 30)),
            text="Back",
            manager=self.manager
        )

        # Title
        UILabel(
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
                    f"{SERVER_URL}/gather/status",
                    json={"player_name": self.player.name, "stop": True},
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    msg = data.get("message", "Collected.")
                    pygame.event.post(pygame.event.Event(pygame.USEREVENT, {"status_message": msg}))
            except Exception as e:
                pygame.event.post(pygame.event.Event(pygame.USEREVENT, {"status_message": "Collection failed."}))
            self.refresh_status()  # Re-check if player is still gathering

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

    def update(self, time_delta):
        self.manager.update(time_delta)

    def draw(self, surface):
        self.manager.draw_ui(surface)

    def teardown(self):
        self.back_button.kill()
        self.status_label.kill()
        self.collect_button.kill()
        self.status_panel.kill()
        for btn in self.buttons:
            btn.kill()
        for lbl in self.level_labels:
            lbl.kill()


ScreenRegistry.register("gathering", GatheringScreen)
