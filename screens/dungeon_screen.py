import time
import random
import pygame
import pygame_gui
import requests
from pygame import Rect
from pygame_gui.elements import UILabel, UIButton, UITextBox

from enemies import ENEMY_TIERS, NAME_PREFIXES, ELITE_AURA_COLORS
from screen_manager import BaseScreen
from screen_registry import ScreenRegistry
from chat_system import ChatWindow
from settings import SERVER_URL


class DungeonScreen(BaseScreen):
    def __init__(self, manager, screen_manager):
        super().__init__(manager, screen_manager)
        self.manager = manager
        self.screen_manager = screen_manager
        self.player = screen_manager.player
        self.level = self.player.dungeon_stats.get("current_level", 1)

        self.battle_running = True
        self.player_attack_timer = 0
        self.enemy_attack_timer = 0

        self.pending_enemy_spawn = False
        self.enemy_spawn_timer = 0.0
        self.enemy_spawn_delay = 1.0  # 1 second delay

        self.player_hp = self.player.total_stats.get("Health", 100)
        self.player_attack_speed = self.player.total_stats.get("Attack Speed", 1.0)
        self.player_attack_delay = max(0.2, 1.0 / self.player_attack_speed)

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

        # Battle log data
        self.battle_log = []

        self.player.chat_window = ChatWindow(self.manager, self.player, self.screen_manager)
        self.player.chat_window.panel.set_relative_position((10, 480))
        self.player.chat_window.panel.set_dimensions((400, 220))

        self.load_enemies()

        # Set up current enemy
        self.set_next_enemy()

    def add_log(self, text):
        self.battle_log.append(text)
        self.battle_log = self.battle_log[-15:]  # Limit to last 15 messages
        self.log_box.set_text("<br>".join(self.battle_log))


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
        self.battle_log = []
        if self.current_enemy_index < 10:
            self.current_enemy = self.enemies[self.current_enemy_index]
            self.current_enemy_index += 1
            self.progress_label.set_text(f"Enemy {self.current_enemy_index} of 10")
        else:
            self.current_enemy = self.boss
            self.progress_label.set_text("Final Boss")
        self.enemy_attack_speed = self.current_enemy.get("speed", 1.0)
        self.enemy_attack_delay = max(0.2, 1.0 / self.enemy_attack_speed)
        self.battle_running = True
        self.player_hp = self.player.total_stats.get("Health", 100)
        self.player_attack_timer = 0
        self.enemy_attack_timer = 0
        self.add_log(f"You engage {self.current_enemy['name']}!")

    def player_attack(self):
        if not self.battle_running:
            return

        weapon = self.player.equipment.get("primary")
        if weapon:
            min_dmg = weapon["stats"].get("Min Damage", 1)
            max_dmg = weapon["stats"].get("Max Damage", 5)
            base_weapon_dmg = random.randint(min_dmg, max_dmg)
        else:
            base_weapon_dmg = 2  # default fallback

        bonus = self.player.total_stats.get("Bonus Damage", 0)

        self.player_damage = base_weapon_dmg + bonus

        dmg = self.player_damage

        # 🎯 Get crit stats
        crit_chance = self.player.total_stats.get("Critical Chance", 0)
        crit_damage = self.player.total_stats.get("Critical Damage", 0)

        # 🎲 Roll for crit
        is_crit = random.random() < (crit_chance / 100)
        if is_crit:
            dmg = int(dmg * (1 + crit_damage / 100))
            self.add_log(f"<font color='#ffcc00'>CRIT!</font> You hit {self.current_enemy['name']} for {dmg} damage!")
        else:
            self.add_log(f"You hit {self.current_enemy['name']} for {dmg} damage.")

        self.current_enemy["hp"] -= dmg
        self.damage_dealt += dmg

        if self.current_enemy["hp"] <= 0:
            self.current_enemy["hp"] = 0
            self.battle_running = False
            self.add_log(f"{self.current_enemy['name']} is defeated!")

            if self.current_enemy.get("is_boss"):
                self.complete_dungeon()
            else:
            # Automatically start new battle
                self.pending_enemy_spawn = True
                self.enemy_spawn_timer = 0.0
        self.update_hp_display()

    def enemy_attack(self):
        if not self.battle_running:
            return

        base_dmg = self.current_enemy["damage"]
        crit_chance = self.current_enemy.get("crit_chance", 0)
        crit_damage = self.current_enemy.get("crit_damage", 0)

        dodge_chance = self.player.total_stats.get("Dodge", 0)
        avoid_chance = self.player.total_stats.get("Avoidance", 0)
        block_chance = self.player.total_stats.get("Block", 0)
        armor = self.player.total_stats.get("Armor", 0)

        # Dodge
        if random.random() < (dodge_chance / 100):
            self.add_log(f"<font color='#00ffff'>You dodged the attack!</font>")
            return

        # Avoidance
        if random.random() < (avoid_chance / 100):
            self.add_log(f"<font color='#00ffff'>You avoided the attack!</font>")
            return

        # Crit
        is_crit = random.random() < (crit_chance / 100)
        dmg = base_dmg
        if is_crit:
            dmg = int(dmg * (1 + crit_damage / 100))

        # Block
        if random.random() < (block_chance / 100):
            dmg = int(dmg * 0.5)
            self.add_log(f"<font color='#aaaaff'>You blocked the attack!</font> Damage reduced.")

        # Armor application (after all multipliers)
        dmg_after_armor = max(0, dmg - armor)

        if dmg_after_armor <= 0:
            self.add_log(f"<font color='#cccccc'>Your armor absorbed all damage!</font>")
        else:
            if is_crit:
                self.add_log(
                    f"<font color='#ff3333'>CRITICAL!</font> {self.current_enemy['name']} hits you for {dmg_after_armor} after armor.")
            else:
                self.add_log(f"{self.current_enemy['name']} hits you for {dmg_after_armor} after armor.")

        self.player_hp -= dmg_after_armor
        self.damage_taken += dmg_after_armor

        if self.player_hp <= 0:
            self.player_hp = 0
            self.add_log("<font color='#ff4444'>You were slain in the dungeon!</font>")
            self.battle_running = False
            from screens.battle_home_screen import BattleHomeScreen
            self.screen_manager.set_screen(BattleHomeScreen(self.manager, self.screen_manager))

    def update_hp_display(self):
        pass
        # self.enemy_hp_label.set_text(f"HP: {self.enemy['hp']} / {self.enemy['max_hp']}")
        # self.player_hp_label.set_text(f"HP: {max(0, self.player_hp)} / {self.player.total_stats.get('Health', 100)}")
        # self.enemy_hp_pct = max(0, self.enemy["hp"] / self.enemy["max_hp"])
        # self.player_hp_pct = max(0, self.player_hp / self.player.total_stats.get("Health", 100))

    def complete_dungeon(self):
        duration = int(time.time() - self.start_time)
        minutes = duration // 60
        seconds = duration % 60

        self.add_log(f"<font color='#00ff00'>Dungeon Level {self.level} completed!</font>")
        self.add_log(
            f"Time: {minutes}m {seconds}s | Damage Dealt: {self.damage_dealt} | Damage Taken: {self.damage_taken}")

        payload = {
            "username": self.player.username,
            "level_completed": self.level,
            "time_seconds": duration
        }
        try:
            requests.post(f"{SERVER_URL}/dungeon_complete", json=payload)
        except Exception as e:
            self.add_log(f"[Error] Could not report dungeon completion: {e}")

        self.player.dungeon_stats["highest_level"] = max(self.player.dungeon_stats.get("highest_level", 1), self.level)
        self.player.dungeon_stats["best_time"] = min(self.player.dungeon_stats.get("best_time", 99999), duration)

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                from screens.battle_home_screen import BattleHomeScreen
                self.screen_manager.set_screen(BattleHomeScreen(self.manager, self.screen_manager))
        if self.player.chat_window:
            self.player.chat_window.process_event(event)

    def update(self, time_delta):
        if self.battle_running:
            self.player_attack_timer += time_delta
            self.enemy_attack_timer += time_delta

            if self.player_attack_timer >= self.player_attack_delay:
                self.player_attack_timer = 0
                self.player_attack()

            if self.enemy_attack_timer >= self.enemy_attack_delay:
                self.enemy_attack_timer = 0
                self.enemy_attack()

        if self.pending_enemy_spawn:
            self.enemy_spawn_timer += time_delta
            if self.enemy_spawn_timer >= self.enemy_spawn_delay:
                self.set_next_enemy()
                self.pending_enemy_spawn = False


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
        if hasattr(self, "log_box"):
            self.log_box.kill()


ScreenRegistry.register("dungeon", DungeonScreen)
