import pygame
import pygame_gui
import inspect

class ChatInputBar:
    def __init__(self, manager, rect, player):
        self.manager = manager
        self.rect = rect
        self.player = player
        self.input_history = []
        self.history_index = -1

        self.visible = False
        self.defer_focus = False

        self.input_field = pygame_gui.elements.UITextEntryLine(
            relative_rect=rect,
            manager=manager
        )
        self.input_field.hide()

        self.command_list = ["/help", "/status", "/admin", "addCoins", "/commands"]

        self.commands = {
            "addCoins": {
                "func": self.player.inventory.Add_Coins,
                "admin_only": True,
                "aliases": ["ac"],
                "help": "Usage: /addCoins <amount> <coin type>\nAdds coins to your inventory"},
            "admin": {
                "func": self.player.toggle_admin,
                "admin_only": False,
                "aliases": [],
                "help": "Usage: /admin <password>\nEnables or disables the admin functionality"},
            "commands": {
                "func": self.list_commands,
                "admin_only": False,
                "aliases": [],
                "help": "Usage: /commands\nLists all available commands (no descriptions)."},
            "status": {
                "func": self.player.status,
                "admin_only": False,
                "aliases": [],
                "help": "Usage: /status\nReturns your admin status."}
        }
        self.alias_map = {}
        for cmd_name, data in self.commands.items():
            for alias in data.get("aliases", []):
                self.alias_map[alias] = cmd_name

    def toggle(self):
        if not self.input_field.is_focused:
            self.visible = not self.visible
            if self.visible:
                self.input_field.show()
                self.input_field.set_text("")
                self.defer_focus = True
            else:
                self.input_field.unfocus()
                self.input_field.hide()

    def update(self):
        if self.defer_focus:
            self.input_field.focus()
            self.defer_focus = False

    def process_events(self, event):
        #Autocomplete Code
        if event.type == pygame_gui.UI_TEXT_ENTRY_CHANGED and event.ui_element == self.input_field:
            user_input = self.input_field.get_text()

            if user_input.startswith("/"):
                suggestions = [cmd for cmd in self.command_list if cmd.startswith(user_input)]
                if suggestions:
                    # Autocomplete (show the first match)
                    self.input_field.set_text(suggestions[0])
                    #self.input_field.set_text_cursor_position(len(user_input))  # Move cursor back to user's current typing point
        #Proccessing Submitted commands
        if event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED and event.ui_element == self.input_field:
            user_input = event.text.strip()
            self.input_field.set_text("")
            self.input_field.unfocus()
            self.input_field.hide()
            self.visible = False

            if user_input:
                self.input_history.append(user_input)
                self.history_index = len(self.input_history)  # reset index after sending
                if user_input.startswith("/"):
                    self.handle_command(user_input)
                else:
                    self.player.log_message(user_input, "chat")

        if event.type == pygame.KEYDOWN and self.visible:
            if event.key == pygame.K_UP:
                if self.input_history and self.history_index > 0:
                    self.history_index -= 1
                    self.input_field.set_text(self.input_history[self.history_index])
                    self.input_field.focus()
            elif event.key == pygame.K_DOWN:
                if self.input_history and self.history_index < len(self.input_history) - 1:
                    self.history_index += 1
                    self.input_field.set_text(self.input_history[self.history_index])
                    self.input_field.focus()
                else:
                    self.input_field.set_text("")


    def handle_command(self, user_input):
        parts = user_input[1:].split()
        command = parts[0]
        args = parts[1:]

        if command == "help":
            if not args:
                self.player.log_message("[Help] Available commands:", "system")
                for cmd_name, cmd_data in self.commands.items():
                    if not cmd_data["admin_only"] or self.player.is_admin:
                        aliases = cmd_data.get("aliases", [])
                        alias_text = f" ({', '.join(aliases)})" if aliases else ""

                        help_line = cmd_data.get("help", "").split('\n')[0]  # just show first line
                        self.player.log_message(f"  /{cmd_name}{alias_text} - {help_line}", "system")
            else:
                help_target = args[0]

                if help_target in self.alias_map:
                    help_target = self.alias_map[help_target]

                if help_target in self.commands:
                    if self.commands[help_target]["admin_only"] and not self.player.is_admin:
                        self.player.log_message("[Access Denied] This command is for admins only.", "system")
                    else:
                        self.player.log_message((self.commands[help_target].get("help",
                                                                                "[Help] No help available for this command."),
                                                 "system"))
                else:
                    self.player.log_message(f"[Help] Unknown command: {help_target}", "system")
            return

        resolved_command = command
        if command not in self.commands and command in self.alias_map:
            resolved_command = self.alias_map[command]

        if resolved_command in self.commands:
            command_entry = self.commands[resolved_command]
            func = command_entry["func"]

            if command_entry["admin_only"] and not self.player.is_admin:
                self.player.log_message("[Access Denied] Admin-only command.", "system")
            else:
                try:
                    sig = inspect.signature(func)
                    params = [
                        p for p in sig.parameters.values()
                        if p.kind in (inspect.Parameter.POSITIONAL_ONLY,
                                      inspect.Parameter.POSITIONAL_OR_KEYWORD)
                    ]
                    required_params = [
                        p for p in params
                        if p.default == inspect.Parameter.empty
                    ]
                    param_names = [p.name for p in required_params]

                    if len(args) < len(required_params):
                        self.player.log_message(f"[Error] Too few arguments for '{command}'.", "system")
                        self.player.log_message(f"Required: {', '.join(param_names)}", "system")
                    elif len(args) > len(params):
                        self.player.log_message(
                            f"[Error] Too many arguments for '{command}'. Max allowed: {len(params)}.\nUse /help {command} for more information",
                            "system")
                    else:
                        func(*args)

                except Exception as e:
                    self.player.log_message(f"[Error] Command failed: {e}", "system")
        else:
            self.player.log_message("No Command Found", "system")

    def list_commands(self):
        self.player.log_message("[Commands] Type /help <command> for usage.", "system")
        for cmd_name, cmd_data in self.commands.items():
            if not cmd_data["admin_only"] or self.player.is_admin:
                aliases = cmd_data.get("aliases", [])
                alias_text = f" ({', '.join(aliases)})" if aliases else ""
                self.player.log_message(f"  /{cmd_name}{alias_text}", "system")