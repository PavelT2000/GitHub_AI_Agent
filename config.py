import os
from pathlib import Path
from dotenv import load_dotenv

# Определяем путь к .env (на случай, если запуск идет из другой папки)
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    """Глобальный конфиг проекта"""
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
    AI_API_KEY = str(os.getenv("AI_API_KEY"))
    AI_BASE_URL = str(os.getenv("AI_BASE_URL"))
    AI_MODEL = str(os.getenv("AI_MODEL"))
    AI_DEBUG = bool(os.getenv("AI_DEBUG")=="1")
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "20000"))

    if not AI_API_KEY:
        raise ValueError("AI_API_KEY не найден в файле .env")
    if not AI_MODEL:
        raise ValueError("AI_MODEL не найден в файле .env")


settings = Config()