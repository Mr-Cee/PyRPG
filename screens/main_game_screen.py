# screens/main_game_screen.py

import pygame
import pygame_gui
from screen_manager import BaseScreen
from screen_registry import ScreenRegistry

class MainGameScreen(BaseScreen):
    def __init__(self, manager, screen_manager):
        super().__init__(manager, screen_manager)

    def setup(self):
        player = self.screen_manager.player

        self.background_panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect((50, 50), (700, 500)),
            manager=self.manager
        )

        self.player_info_label = pygame_gui.elements.UITextBox(
            html_text=f"<b>{player.name}</b><br>Class: {player.char_class}<br>Level: {player.level}<br>Experience: {player.experience}",
            relative_rect=pygame.Rect((100, 100), (600, 150)),
            manager=self.manager,
            container=self.background_panel
        )

        self.idle_status_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((250, 300), (300, 30)),
            text="You are idling in town...",
            manager=self.manager,
            container=self.background_panel
        )

        self.logout_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((300, 400), (200, 50)),
            text="Logout to Main Menu",
            manager=self.manager,
            container=self.background_panel
        )

        self.earned_gold = 0
        self.idle_timer = 0  # Track seconds spent online idling

    def teardown(self):
        self.background_panel.kill()
        self.player_info_label.kill()
        self.idle_status_label.kill()
        self.logout_button.kill()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.logout_button:
                from screens.character_select_screen import CharacterSelectScreen
                self.screen_manager.set_screen(CharacterSelectScreen(self.manager, self.screen_manager))

    def update(self, time_delta):
        self.manager.update(time_delta)

        self.idle_timer += time_delta
        if self.idle_timer >= 5.0:
            self.earned_gold += 1
            self.idle_timer = 0
            self.idle_status_label.set_text(f"You have earned {self.earned_gold} gold!")

    def draw(self, window_surface):
        self.manager.draw_ui(window_surface)

ScreenRegistry.register("main_game", MainGameScreen)
