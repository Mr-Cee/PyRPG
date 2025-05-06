import pygame
import pygame_gui
from pygame import Rect
from pygame_gui.elements import UIButton, UIPanel, UILabel
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

        # Dungeon Panel
        self.dungeon_panel = UIPanel(
            relative_rect=Rect((GAME_WIDTH-325, 25), (300, 120)),
            manager=self.manager
        )
        self.dungeon_label = UILabel(
            relative_rect=Rect((10, 10), (280, 30)),
            text=f"Highest Dungeon Completed: {self.player.dungeon_stats.get('highest_level', 0)}",
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


    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.quick_button:
                from screens.quick_battle_screen import QuickBattleScreen
                self.screen_manager.set_screen(QuickBattleScreen(self.manager, self.screen_manager))
            elif event.ui_element == self.dungeon_button:
                from screens.dungeon_screen import DungeonScreen
                self.screen_manager.set_screen(DungeonScreen(self.manager, self.screen_manager))
            elif event.ui_element == self.raid_button:
                # Placeholder
                pass
            elif event.ui_element == self.back_button:
                from screens.main_game_screen import MainGameScreen
                self.screen_manager.set_screen(MainGameScreen(self.manager, self.screen_manager))

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

ScreenRegistry.register("battle_home", BattleHomeScreen)