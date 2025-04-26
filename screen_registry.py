class ScreenRegistry:
    _registry = {}

    @classmethod
    def register(cls, name, screen_class):
        cls._registry[name] = screen_class

    @classmethod
    def get(cls, name):
        return cls._registry.get(name)

    @classmethod
    def list_screens(cls):
        return list(cls._registry.keys())