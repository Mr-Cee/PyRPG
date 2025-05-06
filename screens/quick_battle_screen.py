import pygame
import pygame_gui
import requests
from pygame import Rect
from pygame_gui.elements import UIButton, UITextBox, UILabel
from enemies import ENEMY_TIERS, NAME_PREFIXES, ELITE_PREFIXES, ELITE_AURA_COLORS
from chat_system import ChatWindow
from items import create_item
from screen_manager import BaseScreen
from screen_registry import ScreenRegistry
import random

from settings import CLASS_WEAPON_RESTRICTIONS, CLASS_PRIMARIES, CLASS_SECONDARIES, SERVER_URL

MAX_DUNGEON_LEVEL=1

class QuickBattleScreen(BaseScreen):
    def __init__(self, manager, screen_manager):
        super().__init__(manager, screen_manager)
        self.player = self.screen_manager.player
        self.manager = manager

        self.player.chat_window = ChatWindow(self.manager, self.player, self.screen_manager)
        self.player.chat_window.panel.set_relative_position((10, 480))
        self.player.chat_window.panel.set_dimensions((400, 220))

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
        self.player_attack_timer = 0
        self.enemy_attack_timer = 0

        self.enemy = self.generate_enemy_from_dungeon_level(self.player.level)
        # self.enemy = self.generate_enemy_from_dungeon_level(MAX_DUNGEON_LEVEL)

        self.player_hp = self.player.total_stats.get("Health", 100)
        # self.player_damage = self.player.total_stats.get("Bonus Damage", 1) + 5

        self.player_attack_speed = self.player.total_stats.get("Attack Speed", 1.0)
        self.enemy_attack_speed = self.enemy.get("speed", 1.0)

        self.player_attack_delay = max(0.2, 1.0 / self.player_attack_speed)
        self.enemy_attack_delay = max(0.2, 1.0 / self.enemy_attack_speed)

        elite_type = self.enemy.get("elite_type")
        color = ELITE_AURA_COLORS.get(elite_type, "#FFFFFF")
        colored_name = f"<font color='{color}'>{self.enemy['name']}</font>"

        # Enemy Name (with color)
        elite_type = self.enemy.get("elite_type")
        color = ELITE_AURA_COLORS.get(elite_type, "#FFFFFF")
        colored_name = f"<font color='{color}'><b>{self.enemy['name']}</b></font>"


        # Enemy Title (e.g., "Elite", "Mythic", etc.)
        title_text = f"<i>{elite_type}</i>" if elite_type else ""
        self.enemy_title_label = UITextBox(
            html_text=title_text,
            relative_rect=Rect((420, 20), (200, 35)),
            manager=self.manager,
            object_id="#enemy_title_label"
        )

        # Enemy name
        self.enemy_name_label = UITextBox(
            html_text=colored_name,
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

        self.update_hp_display()
        self.add_log(f"You engage a {self.enemy['name']}!")

    def update_enemy_name_display(self):
        elite_type = self.enemy.get("elite_type")
        color = ELITE_AURA_COLORS.get(elite_type, "#FFFFFF")
        colored_name = f"<font color='{color}'>{self.enemy['name']}</font>"
        self.enemy_name_label.set_text(colored_name)

    def update_enemy_labels(self):
        elite_type = self.enemy.get("elite_type")
        color = ELITE_AURA_COLORS.get(elite_type, "#FFFFFF")
        colored_name = f"<font color='{color}'><b>{self.enemy['name']}</b></font>"
        self.enemy_name_label.set_text(colored_name)

        title_text = f"<i>{elite_type}</i>" if elite_type else ""
        self.enemy_title_label.set_text(title_text)

    def generate_enemy_from_dungeon_level(self, level):
        # Find highest tier
        tier = ENEMY_TIERS[0]
        for t in ENEMY_TIERS:
            if level >= t["min_level"]:
                tier = t
            else:
                break

        is_elite = random.random() < 0.15  # 15% chance to be elite
        prefix = random.choice(NAME_PREFIXES)

        base_name = f"{random.choice(NAME_PREFIXES)} {tier['name']} Lv{level}"

        elite_type = None
        if is_elite:
            elite_type = random.choice(list(ELITE_AURA_COLORS.keys()))


            # Do not modify name — show elite_type in title only
        name = base_name

        hp = int(tier["base_hp"] + level * 5)
        dmg = int(tier["base_dmg"] + level * 1.5)
        crit_chance = 10 + level * 0.5  # scale slightly with dungeon level
        crit_damage = 50  # 1.5x damage
        speed = round(max(0.5, tier["base_speed"] - level * 0.02), 2)
        xp = int(tier["base_xp"] + level * 2.5)
        copper = int(tier["base_copper"] + level * 15)

        if is_elite:
            hp = int(hp * 1.6)
            dmg = int(dmg * 1.5)
            speed = max(speed - 0.1, 0.5)
            xp = int(xp * 2)
            copper = int(copper * 1.75)

        return {
            "name": name,
            "hp": hp,
            "max_hp": hp,
            "damage": dmg,
            "speed": speed,
            "reward_xp": xp,
            "reward_copper": copper,
            "elite": is_elite,
            "elite_type": elite_type,
            "crit_chance": crit_chance,
            "crit_damage": crit_damage
        }

    def update_hp_display(self):
        self.enemy_hp_label.set_text(f"HP: {self.enemy['hp']} / {self.enemy['max_hp']}")
        self.player_hp_label.set_text(f"HP: {max(0, self.player_hp)} / {self.player.total_stats.get('Health', 100)}")
        self.enemy_hp_pct = max(0, self.enemy["hp"] / self.enemy["max_hp"])
        self.player_hp_pct = max(0, self.player_hp / self.player.total_stats.get("Health", 100))

    def add_log(self, text):
        self.battle_log.append(text)
        self.battle_log = self.battle_log[-15:]
        self.log_box.set_text("<br>".join(self.battle_log))

    def update(self, time_delta):
        self.manager.update(time_delta)

        if self.battle_running:
            self.player_attack_timer += time_delta
            self.enemy_attack_timer += time_delta

            if self.player_attack_timer >= self.player_attack_delay:
                self.player_attack_timer = 0
                self.player_attack()

            if self.enemy_attack_timer >= self.enemy_attack_delay:
                self.enemy_attack_timer = 0
                self.enemy_attack()

        if self.player.chat_window:
            self.player.chat_window.update(time_delta)

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
            self.add_log(f"<font color='#ffcc00'>CRIT!</font> You hit {self.enemy['name']} for {dmg} damage!")
        else:
            self.add_log(f"You hit {self.enemy['name']} for {dmg} damage.")

        self.enemy["hp"] -= dmg
        self.add_log(f"You hit {self.enemy['name']} for {dmg} damage.")

        if self.enemy["hp"] <= 0:
            self.enemy["hp"] = 0
            self.battle_running = False
            self.add_log(f"{self.enemy['name']} is defeated!")
            self.apply_battle_rewards()
        self.update_hp_display()

    def enemy_attack(self):
        if not self.battle_running:
            return

        raw_dmg = self.enemy["damage"]
        crit_chance = self.enemy.get("crit_chance", 0)
        crit_damage = self.enemy.get("crit_damage", 0)
        armor = self.player.total_stats.get("Armor", 0)

        # Roll for crit
        is_crit = random.random() < (crit_chance / 100)
        if is_crit:
            crit_dmg = int(raw_dmg * (1 + crit_damage / 100))
            reduced_dmg = int(crit_dmg * (100 / (100 + armor)))  # Damage mitigation formula
            self.add_log(f"<font color='#ff3333'>CRITICAL HIT!</font> {self.enemy['name']} hits you for {reduced_dmg} damage.")
        else:
            reduced_dmg = int(raw_dmg * (100 / (100 + armor)))  # Damage mitigation formula
            self.add_log(f"{self.enemy['name']} hits you for {reduced_dmg} damage.")

        # reduced_dmg = int(raw_dmg * (100 / (100 + armor)))  # Damage mitigation formula

        self.player_hp -= reduced_dmg


        if self.player_hp <= 0:
            self.player_hp = 0
            self.battle_running = False
            self.add_log("You have been defeated.")

        self.update_hp_display()

    def apply_battle_rewards(self):
        xp = self.enemy.get("reward_xp", 0)
        copper = self.enemy.get("reward_copper", 0)
        self.player.gain_experience(xp)
        self.player.add_coins(copper_amount=copper)
        self.add_log(f"You gain {xp} XP and {copper} copper.")

        # Chance-based item reward
        drop_chance = 0.75 if self.enemy.get("elite") else 0.5
        if random.random() < drop_chance:
            random_slot = random.choice([
                "head", "shoulders", "chest", "gloves", "legs", "boots",
                "primary", "secondary", "amulet", "ring", "bracelet", "belt"
            ])
            random_slot = "primary"
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
                "item_level": MAX_DUNGEON_LEVEL,
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
                    self.show_item_drop_popup(result["item"])
                else:
                    self.add_log(f"[Loot Error] {result.get('error', 'Unknown error')}")
            except Exception as e:
                self.add_log(f"[Loot Error] {str(e)}")

        if self.player.auth_token:
            self.player.sync_coins_to_server(self.player.auth_token)
            self.player.save_to_server(self.player.auth_token)

    def show_item_drop_popup(self, item):
        from pygame import Rect

        stats_lines = [f"<b>{item['name']}</b>"]
        for stat, value in item["stats"].items():
            stats_lines.append(f"{stat}: {value}")
        html_text = "<br>".join(stats_lines)

        self.item_popup = pygame_gui.elements.UIWindow(
            rect=Rect((300, 200), (280, 250)),
            manager=self.manager,
            window_display_title="Item Acquired!",
            object_id="#item_drop_popup"
        )

        pygame_gui.elements.UITextBox(
            html_text=html_text,
            relative_rect=Rect((10, 10), (260, 150)),
            manager=self.manager,
            container=self.item_popup
        )

        self.popup_ok_button = pygame_gui.elements.UIButton(
            relative_rect=Rect((90, 160), (100, 30)),
            text="OK",
            manager=self.manager,
            container=self.item_popup
        )

    def find_free_inventory_slot(self):
        used = {itm.get("slot") for itm in self.player.inventory if isinstance(itm.get("slot"), int)}
        for i in range(50):
            if i not in used:
                return i
        return None

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.back_button:
                from screens.battle_home_screen import BattleHomeScreen
                self.screen_manager.set_screen(BattleHomeScreen(self.manager, self.screen_manager))
            elif hasattr(self, 'popup_ok_button') and event.ui_element == self.popup_ok_button:
                self.item_popup.kill()
                del self.item_popup
                del self.popup_ok_button


        if self.player.chat_window:
            self.player.chat_window.process_event(event)

    def draw_elite_aura(self, surface):
        elite_type = self.enemy.get("elite_type", "Mythic")
        color_hex = ELITE_AURA_COLORS.get(elite_type, "#FFD700")  # fallback to gold
        glow_color = pygame.Color(color_hex)

        center_x = self.enemy_hp_rect.centerx
        center_y = self.enemy_hp_rect.centery

        for i in range(8):  # Layers of aura
            alpha = max(0, 80 - i * 10)
            radius = 40 + i * 4
            aura_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura_surface, (*glow_color[:3], alpha), (radius, radius), radius)
            surface.blit(aura_surface, (center_x - radius, center_y - radius))

    def draw(self, window_surface):
        pygame.draw.rect(window_surface, (100, 0, 0), self.enemy_hp_rect)
        pygame.draw.rect(window_surface, (255, 0, 0),
                         pygame.Rect(self.enemy_hp_rect.x, self.enemy_hp_rect.y,
                                     int(self.enemy_hp_rect.width * self.enemy_hp_pct),
                                     self.enemy_hp_rect.height))

        pygame.draw.rect(window_surface, (0, 100, 0), self.player_hp_rect)
        pygame.draw.rect(window_surface, (0, 255, 0),
                         pygame.Rect(self.player_hp_rect.x, self.player_hp_rect.y,
                                     int(self.player_hp_rect.width * self.player_hp_pct),
                                     self.player_hp_rect.height))

        # if self.enemy.get("elite"):
        #     self.draw_elite_aura(window_surface)

        self.manager.draw_ui(window_surface)

    def teardown(self):
        self.title_label.kill()
        self.back_button.kill()
        self.log_box.kill()
        self.enemy_name_label.kill()
        self.enemy_title_label.kill()
        self.enemy_hp_label.kill()
        self.player_name_label.kill()
        self.player_hp_label.kill()
        if self.player.chat_window:
            self.player.chat_window.teardown()
            self.player.chat_window = None


ScreenRegistry.register("quick_battle", QuickBattleScreen)