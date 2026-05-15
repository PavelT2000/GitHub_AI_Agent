import os
from openai import OpenAI  # Используем универсальный клиент OpenAI
from config import settings
import tiktoken

def get_ai_completion(messages, tools=None, base_url=None, api_key=None, model=None):
    """
    Универсальный метод для работы с OpenAI-совместимыми API (Groq, OpenAI, и т.д.)
    """
    try:
        # Используем переданные параметры или берем дефолтные из конфига
        client = OpenAI(
            base_url=base_url or settings.AI_BASE_URL,
            api_key=api_key or settings.AI_API_KEY
        )
        target_model = model or settings.AI_MODEL

        # --- Блок отладки: Запрос ---
        if settings.AI_DEBUG:
            # Считаем токены (примерно, так как у разных моделей разные токенайзеры)
            token_count = count_tokens(messages, model="gpt-4")

            debug_request = (
                f"{'='*50}\n"
                f"NEW REQUEST | URL: {client.base_url} | Model: {target_model}\n"
                f"{'-'*50}\n"
            )
            for msg in messages:
                debug_request += f"[{msg['role'].upper()}]: {msg['content']}\n"

            if tools:
                debug_request += f"[TOOLS]: {len(tools)} functions attached.\n"

            with open("ai_log.txt", "a", encoding="utf-8") as f:
                f.write(debug_request + "\n")

            print(f"\n[DEBUG] URL: {client.base_url} | Токенов: ~{token_count}")
            user_input = input("Отправить запрос? (y/n): ").lower()
            if user_input != 'y':
                return "Отмена пользователем."

        # --- Выполнение запроса ---
        params = {
            "messages": messages,
            "model": target_model,
        }
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        # Этот метод идентичен и для OpenAI, и для Groq
        chat_completion = client.chat.completions.create(**params)

        # --- Блок отладки: Ответ ---
        if settings.AI_DEBUG:
            response_message = chat_completion.choices[0].message
            debug_response = f"{'-'*50}\n[RESPONSE]:\n"

            if response_message.tool_calls:
                for tool in response_message.tool_calls:
                    debug_response += f"Tool Call: {tool.function.name}({tool.function.arguments})\n"
            else:
                debug_response += f"{response_message.content}\n"

            debug_response += f"{'='*50}\n\n"

            with open("ai_log.txt", "a", encoding="utf-8") as f:
                f.write(debug_response)

        return chat_completion

    except Exception as e:
        error_msg = f"Ошибка API: {e}"
        if settings.AI_DEBUG:
            with open("ai_log.txt", "a", encoding="utf-8") as f:
                f.write(f"ERROR: {error_msg}\n\n")
        return error_msg

def count_tokens(messages, model="gpt-4"):
    # Упрощенная заглушка для примера
    try:
        encoding = tiktoken.encoding_for_model(model)
        text = "".join([m["content"] for m in messages if m.get("content")])
        return len(encoding.encode(text))
    except:
        return 0