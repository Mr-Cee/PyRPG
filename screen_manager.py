class ScreenManager:
    def __init__(self):
        self.current_screen = None
        self.player = None

    def set_screen(self, new_screen):
        if self.current_screen:
            self.current_screen.teardown()  # Clean up old screen
        self.current_screen = new_screen
        self.current_screen.setup()  # Initialize new screen

    def handle_event(self, event):
        if self.current_screen:
            self.current_screen.handle_event(event)

    def update(self, time_delta):
        if self.current_screen:
            self.current_screen.update(time_delta)

    def draw(self, window_surface):
        if self.current_screen:
            self.current_screen.draw(window_surface)


class BaseScreen:
    def __init__(self, manager, screen_manager):
        self.manager = manager
        self.screen_manager = screen_manager

    def setup(self):
        pass

    def teardown(self):
        pass

    def handle_events(self, events):
        pass

    def update(self, time_delta):
        pass

    def draw(self, window_surface):
        pass