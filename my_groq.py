import os
from groq import Groq
from config import settings
import tiktoken
import re

def get_groq_completion(messages, tools=None, model=None):
    try:
        client = Groq(api_key=settings.AI_API_KEY)
        target_model = settings.AI_MODEL

        # --- Блок отладки: Запрос (Request) ---
        if settings.AI_DEBUG:
            token_count = count_tokens(messages, model="gpt-4")

            debug_request = (
                f"{'='*50}\n"
                f"NEW REQUEST | Model: {target_model} | Tokens: {token_count}\n"
                f"{'-'*50}\n"
            )
            for msg in messages:
                debug_request += f"[{msg['role'].upper()}]: {msg['content']}\n"

            if tools:
                debug_request += f"[TOOLS]: {len(tools)} functions attached.\n"

            # Записываем запрос сразу
            with open("ai_log.txt", "a", encoding="utf-8") as f:
                f.write(debug_request + "\n")

            # Подтверждение в консоли
            print(f"\n[DEBUG] Токенов: {token_count}")
            user_input = input("Отправить запрос в Groq? (y/n): ").lower()
            if user_input != 'y':
                with open("ai_log.txt", "a", encoding="utf-8") as f:
                    f.write("CANCELLED BY USER\n\n")
                return "Отмена пользователем."

        # --- Выполнение запроса ---
        params = {
            "messages": messages,
            "model": target_model,
        }
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        chat_completion = client.chat.completions.create(**params)

        # --- Блок отладки: Ответ (Response) ---
        if settings.AI_DEBUG:
            response_message = chat_completion.choices[0].message

            debug_response = f"{'-'*50}\n[RESPONSE]:\n"

            if response_message.tool_calls:
                # Если модель вызвала функции, сохраняем их имена и аргументы
                for tool in response_message.tool_calls:
                    debug_response += f"Tool Call: {tool.function.name}({tool.function.arguments})\n"
            else:
                debug_response += f"{response_message.content}\n"

            debug_response += f"{'='*50}\n\n"

            # Дописываем ответ в тот же файл
            with open("ai_log.txt", "a", encoding="utf-8") as f:
                f.write(debug_response)

        return chat_completion

    except Exception as e:
        error_msg = f"Произошла ошибка: {e}"
        if settings.AI_DEBUG:
            with open("ai_log.txt", "a", encoding="utf-8") as f:
                f.write(f"ERROR: {error_msg}\n\n")
        return error_msg



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
    """Очищает ответ ИИ, извлекая строки из блоков кода или просто списком."""
    # 1. Пробуем вытащить содержимое блоков кода ```...```
    code_blocks = re.findall(r'```(?:\w+)?\s*([\s\S]*?)```', text)

    lines_to_process = []
    if code_blocks:
        # Если есть блоки кода, работаем только с их содержимым
        for block in code_blocks:
            lines_to_process.extend(block.splitlines())
    else:
        # Если блоков кода нет, берем весь текст
        lines_to_process = text.splitlines()

    final_lines = []
    for line in lines_to_process:
        line = line.strip()
        # Убираем пустые строки, заголовки и маркеры списка (- или *)
        if not line or line.startswith('#'):
            continue
        line = line.lstrip('- ').lstrip('* ')

        # Если строка похожа на путь или паттерн
        if any(char in line for char in ['.', '/', '*']):
            final_lines.append(line)

    return final_lines