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
from settings import *

FIRST_TIME_RARITY_TIERS = {
    "Rare": 75,
    "Epic": 10,
    "Legendary": 10,
    "Mythical": 5
}

class DungeonScreen(BaseScreen):
    def __init__(self, manager, screen_manager, drop_down_level=None):
        super().__init__(manager, screen_manager)
        self.manager = manager
        self.screen_manager = screen_manager
        self.player = screen_manager.player

        if drop_down_level:
            self.level = drop_down_level
        else:
            self.level = self.player.highest_dungeon_completed + 1

        self.battle_running = True
        self.player_attack_timer = 0
        self.enemy_attack_timer = 0
        self.dungeon_complete = False

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
        self.continue_button = UIButton(
            relative_rect=Rect((GAME_WIDTH - 160, 400), (150, 40)),
            text="Continue →",
            manager=self.manager
        )
        self.continue_button.hide()  # only show it after boss is defeated

        self.progress_label = UILabel(Rect((130, 50), (300, 30)), "Enemy 1 of 10", manager=self.manager)
        self.log_box = UITextBox(html_text="", relative_rect=Rect((10, 90), (400, 300)), manager=self.manager)

        # Battle log data
        self.battle_log = []

        self.player.chat_window = ChatWindow(self.manager, self.player, self.screen_manager)
        self.player.chat_window.panel.set_relative_position((10, 480))
        self.player.chat_window.panel.set_dimensions((400, 220))

        # Enemy name
        self.enemy_name_label = UITextBox(
            html_text="",
            relative_rect=Rect((420, 45), (200, 30)),
            manager=self.manager,
            object_id="#enemy_title_label"
        )

        # self.enemy_name_label = UILabel(Rect((420, 50), (200, 30)), text=self.enemy["name"], manager=self.manager)
        self.player_name_label = UILabel(Rect((420, 150), (200, 30)), text=self.player.name, manager=self.manager)

        # Enemy HP label
        self.enemy_hp_label = UITextBox(
            html_text="",
            relative_rect=Rect((420, 75), (200, 30)),
            manager=self.manager,
            object_id="#battle_hp_label"
        )
        self.player_hp_label = UITextBox(
            "",
            Rect((420, 180), (200, 30)),
            manager=self.manager,
            object_id="#battle_hp_label"
        )

        self.enemy_hp_label.background_colour = pygame.Color(0, 0, 0, 0)
        self.player_hp_label.background_colour = pygame.Color(0, 0, 0, 0)
        self.enemy_hp_label.rebuild()
        self.player_hp_label.rebuild()

        # Enemy HP bar (just below label)
        self.enemy_hp_rect = pygame.Rect(420, 108, 200, 20)
        self.player_hp_rect = pygame.Rect(420, 210, 200, 20)

        self.load_enemies()

        # Set up current enemy
        self.set_next_enemy()

        self.update_hp_display()

    def set_level(self, level):
        self.level = int(level)

    def start_dungeon_run(self, level: int):
        self.level = level
        self.current_enemy_index = 0
        self.enemies = []
        self.boss = None
        self.current_enemy = None
        self.run_active = True
        self.dungeon_complete = False

        self.damage_dealt = 0
        self.damage_taken = 0
        self.start_time = time.time()

        self.battle_log = []
        self.log_box.set_text("")


        # Generate first enemy (not boss)
        self.load_enemies()

        # Set up current enemy
        self.set_next_enemy()


        self.update_hp_display()

        self.add_log(f"<b><font color='#aaaaff'>Dungeon Level {level} begins!</font></b>")

        # Reset timers
        self.player_attack_timer = 0
        self.enemy_attack_timer = 0
        self.battle_running = True

        self.level_label.set_text(f"Dungeon Level {self.level}")

        # Hide continue button if it's visible
        if hasattr(self, "continue_button"):
            self.continue_button.hide()

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
            if int(level) >= t["min_level"]:
                return t
        return ENEMY_TIERS[0]

    def generate_enemy(self, tier, is_boss=False):
        name = f"{random.choice(NAME_PREFIXES)} {tier['name']} Lv{self.level}"
        hp = int(tier["base_hp"] + int(self.level) * 7)
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
        self.update_hp_display()

    def player_attack(self):
        if not self.battle_running:
            return

        primary_weapon = self.player.equipment.get("primary")
        if primary_weapon:
            min_dmg = primary_weapon["stats"].get("Min Damage", 1)
            max_dmg = primary_weapon["stats"].get("Max Damage", 5)
            base_primary_dmg = random.randint(min_dmg, max_dmg)
        else:
            base_primary_dmg = 2  # default fallback

        secondary_weapon = self.player.equipment.get("secondary")
        if secondary_weapon:
            min_dmg = secondary_weapon["stats"].get("Min Damage", 1)
            max_dmg = secondary_weapon["stats"].get("Max Damage", 5)
            base_secondary_dmg = random.randint(min_dmg, max_dmg)
        else:
            base_secondary_dmg = 2  # default fallback

        bonus = self.player.total_stats.get("Bonus Damage", 0)

        self.player_damage = base_primary_dmg + base_secondary_dmg + bonus

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
        self.enemy_hp_label.set_text(f"HP: {self.current_enemy['hp']} / {self.current_enemy['max_hp']}")
        self.player_hp_label.set_text(f"HP: {max(0, self.player_hp)} / {self.player.total_stats.get('Health', 100)}")
        self.enemy_hp_pct = max(0, self.current_enemy["hp"] / self.current_enemy["max_hp"])
        self.player_hp_pct = max(0, self.player_hp / self.player.total_stats.get("Health", 100))

    def update_enemy_labels(self):
        self.enemy_name_label.set_text(self.current_enemy['name'])

    def complete_dungeon(self):
        duration = int(time.time() - self.start_time)
        minutes = duration // 60
        seconds = duration % 60

        self.apply_dungeon_rewards()

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

        self.player.highest_dungeon_completed = max(self.player.highest_dungeon_completed, self.level)
        self.player.best_dungeon_time_seconds = min(self.player.best_dungeon_time_seconds, duration)

        self.dungeon_complete = True
        self.continue_button.show()

    def apply_dungeon_rewards(self):
        base_xp = 100 + self.level * 20
        base_copper = 250 + self.level * 25

        # Give more on first-time completion
        first_time = self.level > self.player.highest_dungeon_completed
        xp_reward = int(base_xp * (2.0 if first_time else 1.0))
        copper_reward = int(base_copper * (2.0 if first_time else 1.0))

        self.player.gain_experience(xp_reward)
        self.player.add_coins(copper_amount=copper_reward)
        self.add_log(f"<b>Dungeon Complete!</b><br>You earned {xp_reward} XP and {copper_reward} copper!")
        self.player.chat_window.log_message(f"Dungeon Complete!\nYou earned {xp_reward} XP and {copper_reward} copper!", "System")

        # 📦 Guaranteed item drop + better drop on first clear
        drop_chance = 1 if first_time else 0.25
        if random.random() < drop_chance:
            self.grant_dungeon_loot(first_time)

    def grant_dungeon_loot(self, first_time=False):
        rarity = self.pick_rarity(first_time)
        random_slot = random.choice([
            "head", "shoulders", "chest", "gloves", "legs", "boots",
            "primary", "secondary", "amulet", "ring", "bracelet", "belt"
        ])
        char_class = self.player.char_class
        weapon_type = None
        if random_slot == "primary":
            weapon_type = random.choice(CLASS_PRIMARIES.get(char_class, []))
        elif random_slot == "secondary":
            weapon_type = random.choice(CLASS_SECONDARIES.get(char_class, []))
        payload = {
            "slot_type": random_slot,
            "char_class": char_class,
            "weapon_type": weapon_type,
            "rarity": rarity,
            "item_level": self.level,
            "target": self.player.name
        }
        if weapon_type:
            payload["weapon_type"] = weapon_type
        try:
            response = requests.post(f"{SERVER_URL}/createitem", json=payload)
            result = response.json()
            if result.get("success"):
                self.add_log(result["message"])
                # Optionally show the item popup if you also want to show what was dropped
                # You could refetch inventory and search for newest item to show
                # self.show_item_drop_popup(result["item"])
            else:
                self.add_log(f"[Loot Error] {result.get('error', 'Unknown error')}")
        except Exception as e:
            self.add_log(f"[Loot Error] {str(e)}")

    def pick_rarity(self, rng=None, rarity_override=None, first_time=False):
        if first_time:
            if rarity_override:
                return rarity_override
            rng = rng or random.random()
            threshold = 0
            for rarity, chance in FIRST_TIME_RARITY_TIERS.items():
                threshold += chance / 100
                if rng < threshold:
                    return rarity
            return "Rare"  # fallback
        else:
            if rarity_override:
                return rarity_override
            rng = rng or random.random()
            threshold = 0
            for rarity, chance in RARITY_TIERS.items():
                threshold += chance / 100
                if rng < threshold:
                    return rarity
            return "Common"  # fallback

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                from screens.battle_home_screen import BattleHomeScreen
                self.screen_manager.set_screen(BattleHomeScreen(self.manager, self.screen_manager))
            elif event.ui_element == self.continue_button:
                self.level += 1
                self.start_dungeon_run(self.level)  # Reset all combat state
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
        pygame.draw.rect(surface, (100, 0, 0), self.enemy_hp_rect)
        pygame.draw.rect(surface, (255, 0, 0),
                         pygame.Rect(self.enemy_hp_rect.x, self.enemy_hp_rect.y,
                                     int(self.enemy_hp_rect.width * self.enemy_hp_pct),
                                     self.enemy_hp_rect.height))

        pygame.draw.rect(surface, (0, 100, 0), self.player_hp_rect)
        pygame.draw.rect(surface, (0, 255, 0),
                         pygame.Rect(self.player_hp_rect.x, self.player_hp_rect.y,
                                     int(self.player_hp_rect.width * self.player_hp_pct),
                                     self.player_hp_rect.height))

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
        self.continue_button.kill()
        self.enemy_name_label.kill()
        self.enemy_hp_label.kill()
        self.player_name_label.kill()
        self.player_hp_label.kill()


ScreenRegistry.register("dungeon", DungeonScreen)
