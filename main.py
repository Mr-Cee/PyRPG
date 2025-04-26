# main.py
import pygame
import pygame_gui
from screen_manager import ScreenManager
from screen_registry import ScreenRegistry
from autoload_screens import autoload_screens

pygame.init()

# Screen setup
pygame.display.set_caption("Test RPG")
window_surface = pygame.display.set_mode((800, 600))
ui_manager = pygame_gui.UIManager((800, 600))

clock = pygame.time.Clock()

# 🚀 Load all screens automatically
autoload_screens()

# 🚀 Create a screen manager and start on the login screen
screen_manager = ScreenManager()

# # Dynamically load 'login' screen
# login_screen_class = ScreenRegistry.get("login")
# if login_screen_class:
#     screen_manager.set_screen(login_screen_class(ui_manager, screen_manager))
screen_manager.set_screen(ScreenRegistry.get("login")(ui_manager, screen_manager))

running = True
while running:
    time_delta = clock.tick(60) / 1000.0

    events = pygame.event.get()

    for event in events:
        if event.type == pygame.QUIT:
            running = False

        ui_manager.process_events(event)   # <<< Must always process first
        screen_manager.handle_event(event) # <<< Pass **single event**, not whole list

    ui_manager.update(time_delta)
    screen_manager.update(time_delta)

    window_surface.fill((0, 0, 0))
    screen_manager.draw(window_surface)
    pygame.display.update()

pygame.quit()
