# screens/main_game_screen.py
from chat_system import ChatWindow, ChatInputBar
import pygame
import pygame_gui
from screen_manager import BaseScreen
from screen_registry import ScreenRegistry
import datetime

class MainGameScreen(BaseScreen):
    def __init__(self, manager, screen_manager):
        super().__init__(manager, screen_manager)
        self.idle_chest_popup_open = False
        self.idle_chest_window = None

    def setup(self):
        self.chat_window = ChatWindow(self.manager)
        self.chat_input = ChatInputBar(self.manager, self.chat_window)

        self.player = self.screen_manager.player
        self.player.last_logout_time = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=10)
        self.player.calculate_idle_rewards()

        self.background_panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect((50, 50), (700, 500)),
            manager=self.manager
        )

        self.player_info_label = pygame_gui.elements.UITextBox(
            html_text=f"<b>{self.player.name}</b><br>Class: {self.player.char_class}<br>Level: {self.player.level}<br>Experience: {self.player.experience}",
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

        self.gold_label = pygame_gui.elements.UILabel(
            relative_rect=pygame.Rect((250, 260), (300, 30)),
            text=f"Gold: {self.player.gold}",
            manager=self.manager,
            container=self.background_panel
        )

        self.chest_icon = pygame.image.load("Assets/GUI/Icons/treasureChest.png").convert_alpha()
        self.chest_icon = pygame.transform.scale(self.chest_icon, (64, 64))  # Resize if needed

        self.earned_gold = 0
        self.idle_timer = 0

    def teardown(self):
        self.background_panel.kill()
        self.player_info_label.kill()
        self.idle_status_label.kill()
        self.logout_button.kill()
        self.gold_label.kill()
        if self.idle_chest_window:
            self.idle_chest_window.kill()


    def update_gold_label(self):
        if self.gold_label:
            self.gold_label.set_text(f"Gold: {self.player.gold}")

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.logout_button:
                from screens.character_select_screen import CharacterSelectScreen
                self.player.last_logout_time = datetime.datetime.now(datetime.UTC)
                self.player.save_to_server(self.screen_manager.auth_token)  # Add this line
                self.screen_manager.set_screen(CharacterSelectScreen(self.manager, self.screen_manager))

            if self.idle_chest_popup_open and event.ui_element == self.idle_chest_button:
                self.claim_idle_rewards()

        if event.type == pygame_gui.UI_CONFIRMATION_DIALOG_CONFIRMED:
            if self.idle_chest_window and event.ui_element == self.idle_chest_window:
                self.claim_idle_rewards()

        self.chat_window.process_event(event)
        self.chat_input.process_event(event)

    def update(self, time_delta):
        self.manager.update(time_delta)

        self.idle_timer += time_delta
        if self.idle_timer >= 5.0:
            self.player.gold += 1  # ✅ Add to real player gold
            self.idle_timer = 0
            self.update_gold_label()  # ✅ New method to update the gold display


        if self.player.pending_idle_rewards and not self.idle_chest_popup_open:
            self.open_idle_rewards_chest()

        if hasattr(self, "idle_chest_button") and self.idle_chest_button:
            self.idle_chest_button.set_image(self.chest_icon)

        self.chat_window.update(time_delta)
        self.chat_input.update(time_delta)

    def draw(self, window_surface):
        self.manager.draw_ui(window_surface)

    def open_idle_rewards_chest(self):
        self.idle_chest_popup_open = True

        self.idle_chest_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((500, 300), (64, 64)),
            text="",
            manager=self.manager,
            container=self.background_panel,
            tool_tip_text="Click to claim Idle Rewards!",
            object_id="#idle_chest_button"
        )

        # Set the icon again every frame (already doing this)
        self.idle_chest_button.set_image(self.chest_icon)

        # ✅ Make background transparent manually
        self.idle_chest_button.drawable_shape.background_colour = pygame.Color(0, 0, 0, 0)
        self.idle_chest_button.drawable_shape.border_colour = pygame.Color(0, 0, 0, 0)

    def claim_idle_rewards(self):
        if self.player.pending_idle_rewards:
            self.player.experience += self.player.pending_idle_rewards['xp']
            self.player.gold += self.player.pending_idle_rewards['gold']
            self.player.pending_idle_rewards = None
            self.update_gold_label()

        if hasattr(self, "idle_chest_button") and self.idle_chest_button:
            self.idle_chest_button.kill()
            self.idle_chest_button = None

        self.idle_chest_popup_open = False

ScreenRegistry.register("main_game", MainGameScreen)
