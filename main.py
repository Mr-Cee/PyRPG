# main.py
import pygame
import pygame_gui
import requests

from player import Player
from player_registry import unregister_player
from screen_manager import ScreenManager
from screen_registry import ScreenRegistry
from autoload_screens import autoload_screens
from settings import *

pygame.init()

GAME_WIDTH = 1280
GAME_HEIGHT = 720

# Screen setup
pygame.display.set_caption("Test RPG")
window_surface = pygame.display.set_mode((GAME_WIDTH, GAME_HEIGHT))
ui_manager = pygame_gui.UIManager((GAME_WIDTH, GAME_HEIGHT), 'theme.json')

clock = pygame.time.Clock()

# 🚀 Load all screens automatically
autoload_screens()

# 🚀 Create a screen manager and start on the login screen
screen_manager = ScreenManager(ui_manager)

# Normal login flow
login_class = ScreenRegistry.get("login")
if login_class:
    screen_manager.set_screen(login_class(ui_manager, screen_manager))

running = True
while running:
    time_delta = clock.tick(60) / 1000.0

    events = pygame.event.get()

    for event in events:
        if event.type == pygame.QUIT:
            # When the game is quitting or logging out
            try:
                requests.post(
                    f"{SERVER_URL}/logout",
                    json={"username": screen_manager.current_account},
                    timeout=3
                )
            except Exception as e:
                print(f"[Logout] Failed to notify server: {e}")
            running = False

        ui_manager.process_events(event)   # <<< Must always process first
        screen_manager.handle_event(event) # <<< Pass **single event**, not whole list

    ui_manager.update(time_delta)
    screen_manager.update(time_delta)

    window_surface.fill((0, 0, 0))
    screen_manager.draw(window_surface)
    pygame.display.update()

pygame.quit()

