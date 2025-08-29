# core/encryption.py

from cryptography.fernet import Fernet
import os
from .utils import get_config_path

# Get the path for the encryption key, storing it alongside the config file.
KEY_PATH = os.path.join(os.path.dirname(get_config_path()), "vibetype.key")

def _generate_key():
    """Generates a new encryption key and saves it to the key path."""
    key = Fernet.generate_key()
    with open(KEY_PATH, "wb") as key_file:
        key_file.write(key)
    return key

def _load_key():
    """Loads the encryption key from the key path, or generates a new one if it doesn't exist."""
    if not os.path.exists(KEY_PATH):
        return _generate_key()
    with open(KEY_PATH, "rb") as key_file:
        return key_file.read()

# Load the key on module import
_key = _load_key()
_fernet = Fernet(_key)

def encrypt(data: str) -> str:
    """Encrypts a string and returns it as a string."""
    if not data:
        return data
    try:
        # The data needs to be in bytes
        encrypted_data = _fernet.encrypt(data.encode('utf-8'))
        return encrypted_data.decode('utf-8')
    except Exception as e:
        print(f"Encryption failed: {e}")
        return data # Return original data if encryption fails

def decrypt(encrypted_data: str) -> str:
    """Decrypts a string and returns it."""
    if not encrypted_data:
        return encrypted_data
    try:
        # The data needs to be in bytes
        decrypted_data = _fernet.decrypt(encrypted_data.encode('utf-8'))
        return decrypted_data.decode('utf-8')
    except Exception as e:
        # This can happen if the data is not valid encrypted data (e.g., old config)
        # or if the key is wrong. We return the data as is.
        return encrypted_data # Return original data if decryption fails
