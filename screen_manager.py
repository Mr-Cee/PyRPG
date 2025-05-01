


class ScreenManager:
    def __init__(self, manager):
        self.current_screen = None
        self.player = None
        self.manager = manager

    def force_logout(self, reason="Disconnected"):
        """Cleanly logs the player out and returns to the login screen."""
        print(f"[Logout] Reason: {reason}")

        if hasattr(self, "player") and self.player:
            try:
                self.player.stop_heartbeat()
                if hasattr(self, "auth_token"):
                    self.player.save_to_server(self.auth_token)
            except Exception as e:
                print(f"[Logout] Failed to stop/save player: {e}")
            self.player = None

        # Clear any remaining auth state
        self.auth_token = None
        self.current_account = None
        self.player_role = None

        # Switch screen
        from screens.login_screen import LoginScreen
        self.set_screen(LoginScreen(self.manager, self))

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