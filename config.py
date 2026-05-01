import os
from pathlib import Path
from dotenv import load_dotenv

# Определяем путь к .env (на случай, если запуск идет из другой папки)
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    """Глобальный конфиг проекта"""
    GITHUB_TOKEN = str(os.getenv("GITHUB_TOKEN"))
    GROQ_API_KEY = str(os.getenv("GROQ_API_KEY"))
    GROQ_MODEL = str(os.getenv("GROQ_MODEL"))
    # Можно добавить проверку на критические переменные
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN не найден в файле .env")
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY не найден в файле .env")
    if not GROQ_MODEL:
        raise ValueError("GROQ_MODEL не найден в файле .env")
    

settings = Config()