import bcrypt
import json
import os
from cryptography.fernet import Fernet

class AccountManager:
    def __init__(self, filename="Save_Data/game_accounts.json", key_file="Save_Data/encryption.key"):
        self.filename = filename
        self.key_file = key_file
        self.accounts = {}
        self.fernet = None

        self.ensure_save_directory_exists()
        self.load_or_create_key()
        self.load_accounts()

    def ensure_save_directory_exists(self):
        save_dir = os.path.dirname(os.path.abspath(self.filename))
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

    def load_or_create_key(self):
        if not os.path.exists(self.key_file):
            key = Fernet.generate_key()
            with open(self.key_file, "wb") as f:
                f.write(key)
        else:
            with open(self.key_file, "rb") as f:
                key = f.read()

        self.fernet = Fernet(key)

    def load_accounts(self):
        if os.path.exists(self.filename):
            with open(self.filename, "rb") as f:
                encrypted_data = f.read()
                if encrypted_data:
                    decrypted_data = self.fernet.decrypt(encrypted_data)
                    self.accounts = json.loads(decrypted_data.decode('utf-8'))
                else:
                    self.accounts = {}
        else:
            self.accounts = {}

    def save_accounts(self):
        data = json.dumps(self.accounts).encode('utf-8')
        encrypted_data = self.fernet.encrypt(data)
        with open(self.filename, "wb") as f:
            f.write(encrypted_data)

    def register(self, username, password):
        if username in self.accounts:
            return False

        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        self.accounts[username] = {
            "password": hashed.decode('utf-8')
        }
        self.save_accounts()
        self.load_accounts()  # <<< 🚀 Add this line to reload freshly
        return True

    def login(self, username, password):
        if username not in self.accounts:
            return False

        stored_hash = self.accounts[username]["password"].encode('utf-8')
        return bcrypt.checkpw(password.encode('utf-8'), stored_hash)
