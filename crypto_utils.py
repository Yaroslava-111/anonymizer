import base64
import json
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def _derive_key(password, salt):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))


def encrypt_mapping(mapping_dict, password):
    mapping_json = json.dumps(mapping_dict, ensure_ascii=False).encode("utf-8")
    salt = os.urandom(16)
    key = _derive_key(password, salt)
    f = Fernet(key)
    encrypted = f.encrypt(mapping_json)
    return json.dumps({
        "salt": base64.b64encode(salt).decode("utf-8"),
        "data": base64.b64encode(encrypted).decode("utf-8"),
    })


def decrypt_mapping(encrypted_json_str, password):
    envelope = json.loads(encrypted_json_str)
    salt = base64.b64decode(envelope["salt"])
    data = base64.b64decode(envelope["data"])
    key = _derive_key(password, salt)
    f = Fernet(key)
    decrypted = f.decrypt(data)
    return json.loads(decrypted.decode("utf-8"))
