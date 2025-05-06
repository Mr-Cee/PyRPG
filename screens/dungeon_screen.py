import time
import random
import pygame
import pygame_gui
from pygame import Rect
from pygame_gui.elements import UILabel, UIButton, UITextBox

from enemies import ENEMY_TIERS, NAME_PREFIXES, ELITE_AURA_COLORS
from screen_manager import BaseScreen
from screen_registry import ScreenRegistry
from chat_system import ChatWindow

class DungeonScreen(BaseScreen):
    def __init__(self, manager, screen_manager):
        super().__init__(manager, screen_manager)
        self.manager = manager
        self.screen_manager = screen_manager
        self.player = screen_manager.player
        self.level = self.player.dungeon_stats.get("current_level", 1)

        # Dungeon state
        self.current_enemy_index = 0
        self.enemies = []
        self.boss = None
        self.current_enemy = None
        self.run_active = True

        # Run tracking
        self.start_time = time.time()
        self.damage_dealt = 0
        self.damage_taken = 0

        # UI
        self.back_button = UIButton(Rect((10, 10), (100, 30)), "Exit", manager=self.manager)
        self.level_label = UILabel(Rect((130, 10), (300, 30)), f"Dungeon Level {self.level}", manager=self.manager)

        self.progress_label = UILabel(Rect((130, 50), (300, 30)), "Enemy 1 of 10", manager=self.manager)
        self.log_box = UITextBox(html_text="", relative_rect=Rect((10, 90), (400, 300)), manager=self.manager)

        self.player.chat_window = ChatWindow(self.manager, self.player, self.screen_manager)
        self.player.chat_window.panel.set_relative_position((10, 480))
        self.player.chat_window.panel.set_dimensions((400, 220))

        self.load_enemies()

        # Set up current enemy
        self.set_next_enemy()

    def load_enemies(self):
        tier = self.find_tier(self.level)
        self.enemies = [self.generate_enemy(tier) for _ in range(10)]
        self.boss = self.generate_enemy(tier, is_boss=True)

    def find_tier(self, level):
        for t in reversed(ENEMY_TIERS):
            if level >= t["min_level"]:
                return t
        return ENEMY_TIERS[0]

    def generate_enemy(self, tier, is_boss=False):
        name = f"{random.choice(NAME_PREFIXES)} {tier['name']} Lv{self.level}"
        hp = int(tier["base_hp"] + self.level * 7)
        dmg = int(tier["base_dmg"] + self.level * 2)
        if is_boss:
            hp = int(hp * 2)
            dmg = int(dmg * 1.8)
            name = f"BOSS: {name}"

        return {
            "name": name,
            "hp": hp,
            "max_hp": hp,
            "damage": dmg,
            "is_boss": is_boss
        }

    def set_next_enemy(self):
        if self.current_enemy_index < 10:
            self.current_enemy = self.enemies[self.current_enemy_index]
            self.current_enemy_index += 1
            self.progress_label.set_text(f"Enemy {self.current_enemy_index} of 10")
        else:
            self.current_enemy = self.boss
            self.progress_label.set_text("Final Boss")

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                from screens.battle_home_screen import BattleHomeScreen
                self.screen_manager.set_screen(BattleHomeScreen(self.manager, self.screen_manager))
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
        self.level_label.kill()
        self.progress_label.kill()
        self.log_box.kill()
        self.player.chat_window.teardown()
        self.player.chat_window = None


ScreenRegistry.register("dungeon", DungeonScreen)
