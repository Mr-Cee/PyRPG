from server import app

for route in app.routes:
    print(route.path)