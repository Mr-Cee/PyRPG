# player_registry.py
online_players = {}

def register_player(player):
    online_players[player.name.lower()] = player

def get_player(name):
    return online_players.get(name.lower())

def unregister_player(name):
    online_players.pop(name.lower(), None)

def list_online_names():
    return list(online_players.keys())