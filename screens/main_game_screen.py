# screens/main_game_screen.py

from screen_manager import BaseScreen
from screen_registry import ScreenRegistry
import pygame_gui
import pygame


class MainGameScreen(BaseScreen):
    def setup(self):
        self.title_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((200, 100), (400, 50)),
            text="Main Game Screen!",
            manager=self.manager
        )

        self.back_to_login_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((300, 300), (200, 50)),
            text="Logout",
            manager=self.manager
        )

    def teardown(self):
        self.title_label.kill()
        self.back_to_login_button.kill()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_to_login_button:
                login_screen_class = ScreenRegistry.get("login")
                if login_screen_class:
                    self.screen_manager.set_screen(login_screen_class(self.manager, self.screen_manager))

    def update(self, time_delta):
        self.manager.update(time_delta)

    def draw(self, window_surface):
        self.manager.draw_ui(window_surface)


# 🚀 Register this screen
ScreenRegistry.register("main_game", MainGameScreen)
