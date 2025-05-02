# screens/main_game_screen.py
import requests

from chat_system import ChatWindow
import pygame
import pygame_gui
from screen_manager import BaseScreen
from screen_registry import ScreenRegistry
import datetime

from settings import SERVER_URL


class MainGameScreen(BaseScreen):
    def __init__(self, manager, screen_manager):
        super().__init__(manager, screen_manager)
        self.idle_chest_popup_open = False
        self.idle_chest_window = None

    def setup(self):
        self.player = self.screen_manager.player
        self.player.start_heartbeat(self.screen_manager.current_account)
        self.player.last_logout_time = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=10)
        self.player.calculate_idle_rewards()

        self.chat_window = ChatWindow(self.manager, self.player, self.screen_manager)
        self.chat_window.panel.set_relative_position((10, 480))
        self.chat_window.panel.set_dimensions((400, 220))

        self.logout_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((1050, 650), (200, 50)),
            text="Logout to Main Menu",
            manager=self.manager
        )
        # Main Menu Panel
        self.menu_panel = pygame_gui.elements.UIPanel(
            relative_rect=pygame.Rect((10, 10), (150, 250)),  # x, y, width, height
            manager=self.manager
        )
        # Main Menu Buttons
        button_labels = ["Inventory", "Equipment", "Quests", "Skills", "World Map", "Logout"]
        self.menu_buttons = []

        for i, label in enumerate(button_labels):
            btn = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect((10, 10 + i * 40), (130, 30)),
                text=label,
                manager=self.manager,
                container=self.menu_panel
            )
            self.menu_buttons.append(btn)

        self.chest_icon = pygame.image.load("Assets/GUI/Icons/treasureChest.png").convert_alpha()
        self.chest_icon = pygame.transform.scale(self.chest_icon, (64, 64))  # Resize if needed

        self.earned_gold = 0
        self.idle_timer = 0

    def teardown(self):
        self.logout_button.kill()
        if self.idle_chest_window:
            self.idle_chest_window.kill()
        if self.chat_window:
            self.chat_window.teardown()
            self.chat_window = None
        if self.player:
            self.player.stop_heartbeat()
        self.menu_panel.kill()
        if self.idle_chest_button:
            self.idle_chest_button.kill()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.logout_button:
                try:
                    requests.post(
                        f"{SERVER_URL}/logout",
                        json={"username": self.screen_manager.current_account},
                        timeout=3
                    )
                except Exception as e:
                    print(f"[Logout] Failed to notify server: {e}")
                from screens.character_select_screen import CharacterSelectScreen
                self.player.last_logout_time = datetime.datetime.now(datetime.UTC)
                self.player.save_to_server(self.screen_manager.auth_token)  # Add this line
                self.screen_manager.set_screen(CharacterSelectScreen(self.manager, self.screen_manager))

            for btn in self.menu_buttons:
                if event.ui_element == btn:
                    label = btn.text
                    if label == "Inventory":
                        inventory_screen = ScreenRegistry.get("inventory")
                        if inventory_screen:
                            self.screen_manager.set_screen(inventory_screen(self.manager, self.screen_manager))
                        # self.screen_manager.set_screen(InventoryScreen(self.manager, self.screen_manager))
                    elif label == "Logout":
                        self.screen_manager.force_logout("Logged out.")
                    else:
                        print(f"[UI] '{label}' button clicked (hook up later)")

            if self.idle_chest_popup_open and event.ui_element == self.idle_chest_button:
                self.claim_idle_rewards()

        if event.type == pygame_gui.UI_CONFIRMATION_DIALOG_CONFIRMED:
            if self.idle_chest_window and event.ui_element == self.idle_chest_window:
                self.claim_idle_rewards()

        if self.chat_window:
            self.chat_window.process_event(event)


    def update(self, time_delta):
        self.manager.update(time_delta)

        self.player.update_heartbeat(time_delta)

        self.idle_timer += time_delta
        if self.idle_timer >= 5.0:
            self.player.gold += 1  # ✅ Add to real player gold
            self.idle_timer = 0


        if self.player.pending_idle_rewards and not self.idle_chest_popup_open:
            self.open_idle_rewards_chest()

        if hasattr(self, "idle_chest_button") and self.idle_chest_button:
            self.idle_chest_button.set_image(self.chest_icon)

        self.chat_window.update(time_delta)

    def draw(self, window_surface):
        self.manager.draw_ui(window_surface)

    def open_idle_rewards_chest(self):
        self.idle_chest_popup_open = True

        self.idle_chest_button = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((10, 410), (64, 64)),
            text="",
            manager=self.manager,
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
            # Calculate offline duration
            offline_seconds = (datetime.datetime.now(datetime.UTC) - self.player.last_logout_time).total_seconds()
            minutes = int(offline_seconds // 60)
            seconds = int(offline_seconds % 60)

            xp = self.player.pending_idle_rewards['xp']
            gold = self.player.pending_idle_rewards['gold']

            # Log to chat (client-side only)
            reward_summary = f"[Idle Rewards] You were offline for {minutes}m {seconds}s and earned {xp} XP and {gold} Gold."
            self.chat_window.log_message(reward_summary, "System")
            self.player.pending_idle_rewards = None


        if hasattr(self, "idle_chest_button") and self.idle_chest_button:
            self.idle_chest_button.kill()
            self.idle_chest_button = None

        self.idle_chest_popup_open = False

ScreenRegistry.register("main_game", MainGameScreen)
