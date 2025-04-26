# autoload_screens.py

import os
import importlib

def autoload_screens():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    screens_dir = os.path.join(base_dir, 'screens')

    for filename in os.listdir(screens_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = f"screens.{filename[:-3]}"  # Remove '.py'
            importlib.import_module(module_name)