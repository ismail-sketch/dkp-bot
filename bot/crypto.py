"""Шифрование паспортных данных (Fernet). Ключ — в .env или data/secret.key, вне БД."""
from cryptography.fernet import Fernet

from config import ENCRYPTION_KEY

_f = Fernet(ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY)


def encrypt(data: dict) -> str:
    import json
    return _f.encrypt(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode()


def decrypt(token: str) -> dict:
    import json
    return json.loads(_f.decrypt(token.encode()).decode("utf-8"))
