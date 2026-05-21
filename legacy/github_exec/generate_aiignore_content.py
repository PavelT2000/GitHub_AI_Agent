from .get_repo_extensions import get_repo_extensions
from pathlib import Path
from my_repo import MyRepo
from my_groq import get_groq_completion


def generate_aiignore_content(repo: MyRepo) -> str:
    """
    Просит Groq составить .aiignore на основе расширений.
    """
    stats = get_repo_extensions(repo)
    
    if not stats:
        return "# Репозиторий пуст"

    system_prompt = (
        "Ты — ассистент разработчика. Я дам тебе список расширений и файлов из репозитория. "
        "Твоя задача: "
        "1. Определить, какие из них точно являются исходным кодом (например, .py, .js, .cpp, .h). "
        "2. Всё остальное (бинарники, картинки, конфиги окружения, медиа, кэш) помести в список для .aiignore. "
        "3. Также добавь стандартные папки-исключения (venv, node_modules, __pycache__). "
        "Ответь только содержимым файла .aiignore, без лишних слов."
    )
    
    user_prompt = f"Файлы в репозитории '{repo.name}':\n\n{stats}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    completion = get_groq_completion(messages)

    if isinstance(completion, str):
        return "# Ошибка генерации"
    
    return completion.choices[0].message.content.strip()