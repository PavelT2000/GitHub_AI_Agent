import os
from pathlib import Path
from dotenv import load_dotenv

# Определяем путь к .env (на случай, если запуск идет из другой папки)
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    """Глобальный конфиг проекта"""
    GITHUB_TOKEN = str(os.getenv("GITHUB_TOKEN"))
    AI_API_KEY = str(os.getenv("GROQ_API_KEY"))
    AI_BASE_URL=str(os.getenv("AI_BASE_URL"))
    AI_MODEL = str(os.getenv("GROQ_MODEL"))
    AI_DEBUG = bool(os.getenv("AI_DEBUG"))

    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN не найден в файле .env")
    if not AI_API_KEY:
        raise ValueError("GROQ_API_KEY не найден в файле .env")
    if not AI_MODEL:
        raise ValueError("GROQ_MODEL не найден в файле .env")


settings = Config()