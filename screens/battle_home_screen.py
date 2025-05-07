import pygame
import pygame_gui
from pygame import Rect
from pygame_gui.elements import UIButton, UIPanel, UILabel, UIDropDownMenu
from settings import *
from screen_manager import BaseScreen
from screen_registry import ScreenRegistry


class BattleHomeScreen(BaseScreen):
    def __init__(self, manager, screen_manager):
        super().__init__(manager, screen_manager)
        self.player = screen_manager.player

        self.quick_button = UIButton(
            relative_rect=Rect((100, 100), (200, 40)),
            text="Quick Battle",
            manager=manager
        )

        self.dungeon_button = UIButton(
            relative_rect=Rect((100, 160), (200, 40)),
            text="Dungeons",
            manager=manager
        )

        # Dungeon Level Dropdown (positioned next to Dungeon button)
        self.dungeon_levels = [str(i) for i in range(1, self.player.highest_dungeon_completed + 2)][::-1]
        self.selected_dungeon_level = self.dungeon_levels[-1]

        self.dungeon_dropdown = UIDropDownMenu(
            options_list=self.dungeon_levels,
            starting_option=self.selected_dungeon_level,
            relative_rect=Rect((310, 160), (100, 40)),  # Positioned right of the Dungeon button
            manager=self.manager
        )

        # Dungeon Panel
        self.dungeon_panel = UIPanel(
            relative_rect=Rect((GAME_WIDTH-325, 25), (300, 120)),
            manager=self.manager
        )
        self.dungeon_label = UILabel(
            relative_rect=Rect((10, 10), (280, 30)),
            text=f"Highest Dungeon Completed: {self.player.highest_dungeon_completed}",
            manager=self.manager,
            container=self.dungeon_panel
        )

        self.raid_button = UIButton(
            relative_rect=Rect((100, 220), (200, 40)),
            text="Raids",
            manager=manager
        )

        self.back_button = UIButton(
            relative_rect=Rect((100, 300), (200, 40)),
            text="Back",
            manager=manager
        )
        self.leaderboard_panel = UIPanel(
            relative_rect=Rect((GAME_WIDTH - 325, 155), (300, 275)),  # Under the dungeon panel
            manager=self.manager
        )
        self.leaderboard_labels = []  # Track labels so we can clear on reload

        # Title
        UILabel(
            relative_rect=Rect((10, 5), (280, 30)),
            text="🏆 Dungeon Leaderboard",
            manager=self.manager,
            container=self.leaderboard_panel
        )

        self.load_leaderboard()

        self.load_dungeon_stats()

    def load_leaderboard(self):
        import threading
        import requests

        def fetch_leaderboard():
            try:
                response = requests.get(f"{SERVER_URL}/dungeon_leaderboard")
                if response.status_code == 200:
                    data = response.json().get("leaders", [])
                    pygame.time.set_timer(pygame.USEREVENT + 101, 0)  # Stop any previous timer

                    # Clear previous labels
                    for label in self.leaderboard_labels:
                        label.kill()
                    self.leaderboard_labels.clear()

                    for i, entry in enumerate(data):
                        text = f"{i + 1}. {entry['name']} - {entry['dungeon']} ({entry['time']}s)"
                        label = UILabel(
                            relative_rect=Rect((10, 40 + i * 22), (280, 20)),
                            text=text,
                            manager=self.manager,
                            container=self.leaderboard_panel
                        )
                        self.leaderboard_labels.append(label)
            except Exception as e:
                print(f"[Leaderboard] Failed to load: {e}")

        threading.Thread(target=fetch_leaderboard, daemon=True).start()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.quick_button:
                from screens.quick_battle_screen import QuickBattleScreen
                self.screen_manager.set_screen(QuickBattleScreen(self.manager, self.screen_manager))
            elif event.ui_element == self.dungeon_button:
                from screens.dungeon_screen import DungeonScreen
                screen = DungeonScreen(self.manager, self.screen_manager, int(self.selected_dungeon_level))
                # screen.set_level(self.selected_dungeon_level)  # Pass selected level
                self.screen_manager.set_screen(screen)
            elif event.ui_element == self.raid_button:
                # Placeholder
                pass
            elif event.ui_element == self.back_button:
                from screens.main_game_screen import MainGameScreen
                self.screen_manager.set_screen(MainGameScreen(self.manager, self.screen_manager))

        elif event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
            if event.ui_element == self.dungeon_dropdown:
                self.selected_dungeon_level = int(event.text)

    def load_dungeon_stats(self):
        import threading
        import requests

        def fetch_stats():
            try:
                response = requests.get(f"{SERVER_URL}/player_stats?requester_name={self.player.name}")
                if response.status_code == 200:
                    data = response.json()
                    highest = data.get("highest_dungeon_completed", 0)
                    best_time = data.get("best_dungeon_time_seconds", 0)
                    self.player.highest_dungeon_completed = highest
                    self.player.best_dungeon_time_seconds = best_time
                    self.dungeon_label.set_text(f"Highest Dungeon Completed: {highest}")

                    self.dungeon_levels = [str(i) for i in range(1, self.player.highest_dungeon_completed + 2)][::-1]
                    self.selected_dungeon_level = self.dungeon_levels[0]
                    self.dungeon_dropdown.kill()  # Remove old dropdown
                    self.dungeon_dropdown = UIDropDownMenu(
                        options_list=self.dungeon_levels,
                        starting_option=self.selected_dungeon_level,
                        relative_rect=Rect((310, 160), (100, 40)),
                        manager=self.manager
                    )
                else:
                    self.dungeon_label.set_text("Failed to load stats")
            except Exception as e:
                self.dungeon_label.set_text("Error loading stats")



        threading.Thread(target=fetch_stats, daemon=True).start()

    def update(self, time_delta):
        self.manager.update(time_delta)

    def draw(self, window_surface):
        self.manager.draw_ui(window_surface)

    def teardown(self):
        self.quick_button.kill()
        self.dungeon_button.kill()
        self.raid_button.kill()
        self.back_button.kill()
        self.dungeon_panel.kill()
        self.dungeon_dropdown.kill()
        self.leaderboard_panel.kill()
        for label in self.leaderboard_labels:
            label.kill()

ScreenRegistry.register("battle_home", BattleHomeScreen)