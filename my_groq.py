import os
from groq import Groq
from config import settings
import tiktoken
import re

def get_groq_completion(messages, tools=None, model=None):
    """
    Отправляет запрос к Groq API. 
    messages: список словарей [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
    """
    try:
        client = Groq(api_key=settings.GROQ_API_KEY)
        print(f"Запрос на {count_tokens(messages)}")
        # Используем модель из настроек, если не передана явно
        target_model = settings.GROQ_MODEL

        params = {
            "messages": messages,
            "model": target_model,
        }

        # Добавляем инструменты только если они переданы
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        chat_completion = client.chat.completions.create(**params)
        
        return chat_completion

    except Exception as e:
        return f"Произошла ошибка: {e}"
    


def count_tokens(data, model="gpt-4"):
    """
    Считает токены для строки текста или списка сообщений (messages).
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Если модель новая или специфичная, используем базовую кодировку cl100k_base
        encoding = tiktoken.get_encoding("cl100k_base")

    if isinstance(data, str):
        # Если на вход подана просто строка
        return len(encoding.encode(data))
    
    elif isinstance(data, list):
        # Если на вход подан список messages для чата
        num_tokens = 0
        for message in data:
            # Каждый месседж занимает токены под роль, контент и служебные символы
            num_tokens += 4  
            for key, value in message.items():
                num_tokens += len(encoding.encode(value))
        num_tokens += 2  # Ответ помощника тоже требует задела
        return num_tokens
    
    return 0



def clean_ai_response(text: str) -> list:
    """Очищает ответ ИИ от Markdown блоков кода и лишнего текста."""
    # Удаляем блоки кода ```...```
    text = re.sub(r'```[\s\S]*?```', '', text)
    
    lines = []
    for line in text.splitlines():
        line = line.strip()
        # Пропускаем пустые строки, заголовки и строки с пояснениями (содержащие пробелы между слов)
        if not line or line.startswith('#') or ' ' in line:
            continue
        # Если строка похожа на путь или паттерн (нет пробелов, есть точки или слеши)
        if any(char in line for char in ['.', '/', '*']):
            lines.append(line)
    return lines