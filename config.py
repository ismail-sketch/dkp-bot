"""Конфигурация. Все различия сред (ПК / VPS) — только через переменные окружения."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
FONTS_DIR = BASE_DIR / "assets" / "fonts"

for _d in (DATA_DIR, LOGS_DIR, LOGS_DIR / "preview"):
    _d.mkdir(parents=True, exist_ok=True)

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
ADMIN_ID: int = int(os.getenv("ADMIN_ID") or 0)
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{(DATA_DIR / 'app.db').as_posix()}")
# postgresql://... -> явный драйвер, чтобы не переписывать код при переезде
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# --- Шифрование паспортных данных (Fernet) ---
_key_file = DATA_DIR / "secret.key"


def _load_or_create_key() -> str:
    from cryptography.fernet import Fernet

    env_key = os.getenv("ENCRYPTION_KEY", "").strip()
    if env_key:
        return env_key
    if _key_file.exists():
        return _key_file.read_text(encoding="utf-8").strip()
    key = Fernet.generate_key().decode()
    _key_file.write_text(key, encoding="utf-8")
    if os.name == "nt":
        os.system(f'attrib +h "{_key_file}"')
    return key


ENCRYPTION_KEY: str = _load_or_create_key()
