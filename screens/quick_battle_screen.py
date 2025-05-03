import pygame
import pygame_gui
from pygame import Rect
from pygame_gui.elements import UIButton, UITextBox, UILabel

from screen_manager import BaseScreen
from screen_registry import ScreenRegistry
import random


class QuickBattleScreen(BaseScreen):
    def __init__(self, manager, screen_manager):
        super().__init__(manager, screen_manager)
        self.player = self.screen_manager.player
        self.manager = manager

        # UI elements
        self.title_label = UILabel(
            relative_rect=Rect((10, 10), (300, 30)),
            text="Quick Battle - Auto Combat",
            manager=manager
        )

        self.back_button = UIButton(
            relative_rect=Rect((10, 400), (100, 40)),
            text="Back",
            manager=manager
        )

        self.log_box = UITextBox(
            html_text="",
            relative_rect=Rect((10, 50), (380, 340)),
            manager=manager
        )

        self.battle_log = []
        self.battle_running = True
        self.time_accumulator = 0
        self.turn_interval = 1.5  # seconds between turns

        # Setup combatants
        self.enemy = {
            "name": "Slime",
            "hp": 25,
            "max_hp": 25,
            "damage": 5,
            "speed": 1.0,
            "reward_xp": 10,
            "reward_copper": 50
        }

        self.player_hp = self.player.total_stats.get("Health", 100)
        self.player_damage = self.player.total_stats.get("Bonus Damage", 1) + 5  # base damage + bonus

        # Enemy name & HP
        self.enemy_name_label = UILabel(
            relative_rect=Rect((420, 50), (200, 30)),
            text=self.enemy["name"],
            manager=self.manager
        )
        # Player name & HP
        self.player_name_label = UILabel(
            relative_rect=Rect((420, 150), (200, 30)),
            text=self.player.name,
            manager=self.manager
        )
        self.enemy_hp_label = UITextBox(
            html_text="",
            relative_rect=Rect((420, 80), (200, 30)),  # ← was 25, now 30
            manager=self.manager
        )

        self.player_hp_label = UITextBox(
            html_text="",
            relative_rect=Rect((420, 180), (200, 30)),  # ← was 25, now 30
            manager=self.manager
        )

        self.enemy_hp_label.background_colour = pygame.Color(0, 0, 0, 0)
        self.player_hp_label.background_colour = pygame.Color(0, 0, 0, 0)

        self.enemy_hp_label.rebuild()
        self.player_hp_label.rebuild()

        # Bar rectangles (we'll draw them manually)
        self.enemy_hp_rect = pygame.Rect(420, 110, 200, 20)
        self.player_hp_rect = pygame.Rect(420, 210, 200, 20)

        self.update_hp_display()

        self.add_log(f"You engage a {self.enemy['name']}!")
        self.update_hp_display()


    def update_hp_display(self):
        # Labels
        self.enemy_hp_label.set_text(f"HP: {self.enemy['hp']} / {self.enemy['max_hp']}")
        self.player_hp_label.set_text(f"HP: {max(0, self.player_hp)} / {self.player.total_stats.get('Health', 100)}")

        # HP percentages for bar widths
        self.enemy_hp_pct = max(0, self.enemy["hp"] / self.enemy["max_hp"])
        self.player_hp_pct = max(0, self.player_hp / self.player.total_stats.get("Health", 100))

    def add_log(self, text):
        self.battle_log.append(text)
        self.battle_log = self.battle_log[-15:]  # limit to last 15 lines
        formatted = "<br>".join(self.battle_log)
        self.log_box.set_text(formatted)

    def update(self, time_delta):
        self.manager.update(time_delta)

        if self.battle_running:
            self.time_accumulator += time_delta
            if self.time_accumulator >= self.turn_interval:
                self.time_accumulator = 0
                self.run_turn()

    def run_turn(self):
        # Player attacks
        dmg = self.player_damage
        self.enemy["hp"] -= dmg
        self.add_log(f"You hit {self.enemy['name']} for {dmg} damage.")

        if self.enemy["hp"] <= 0:
            self.add_log(f"{self.enemy['name']} is defeated!")
            self.battle_running = False

            # Apply rewards
            xp = self.enemy.get("reward_xp", 0)
            copper = self.enemy.get("reward_copper", 0)

            self.player.gain_experience(xp)
            self.player.add_coins(copper_amount=copper)

            self.add_log(f"You gain {xp} XP and {copper} copper.")

            # Sync to server
            if self.player.auth_token:
                self.player.sync_coins_to_server(self.player.auth_token)
                self.player.save_to_server(self.player.auth_token)
            return

        # Enemy attacks
        enemy_dmg = self.enemy["damage"]
        self.player_hp -= enemy_dmg
        self.add_log(f"{self.enemy['name']} hits you for {enemy_dmg} damage.")

        if self.player_hp <= 0:
            self.add_log("You have been defeated.")
            self.battle_running = False

        self.update_hp_display()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                from screens.battle_home_screen import BattleHomeScreen
                self.screen_manager.set_screen(BattleHomeScreen(self.manager, self.screen_manager))

    def draw(self, window_surface):
        # After manager.draw_ui(window_surface)
        # Enemy HP Bar
        pygame.draw.rect(window_surface, (100, 0, 0), self.enemy_hp_rect)  # Background
        pygame.draw.rect(
            window_surface, (255, 0, 0),
            pygame.Rect(self.enemy_hp_rect.x, self.enemy_hp_rect.y, int(self.enemy_hp_rect.width * self.enemy_hp_pct),
                        self.enemy_hp_rect.height)
        )

        # Player HP Bar
        pygame.draw.rect(window_surface, (0, 100, 0), self.player_hp_rect)  # Background
        pygame.draw.rect(
            window_surface, (0, 255, 0),
            pygame.Rect(self.player_hp_rect.x, self.player_hp_rect.y,
                        int(self.player_hp_rect.width * self.player_hp_pct), self.player_hp_rect.height)
        )


        self.manager.draw_ui(window_surface)

    def teardown(self):
        self.title_label.kill()
        self.back_button.kill()
        self.log_box.kill()
        self.enemy_name_label.kill()
        self.enemy_hp_label.kill()
        self.player_name_label.kill()
        self.player_hp_label.kill()


ScreenRegistry.register("quick_battle", QuickBattleScreen)