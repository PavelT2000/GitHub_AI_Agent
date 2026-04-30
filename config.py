import os
from pathlib import Path
from dotenv import load_dotenv

# Определяем путь к .env (на случай, если запуск идет из другой папки)
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    """Глобальный конфиг проекта"""
    GITHUB_TOKEN = str(os.getenv("GITHUB_TOKEN"))

    # Можно добавить проверку на критические переменные
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN не найден в файле .env")

settings = Config()