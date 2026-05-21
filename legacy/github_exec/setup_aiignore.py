import pathspec
from pathlib import Path
from my_repo import MyRepo
from .generate_aiignore_content import generate_aiignore_content
from my_groq import get_groq_completion, clean_ai_response
from .get_optimized_tree import get_optimized_tree
from .get_repo_extensions import get_repo_extensions


def setup_aiignore(repo: MyRepo):
    """
    Двухэтапный алгоритм генерации правил игнорирования.
    """
    project_root = Path.cwd()
    repo_path = project_root / "temp" / repo.name

    # --- ШАГ 1: Фильтрация по расширениям ---
    stats = get_repo_extensions(repo_path)

    prompt1 = [
        {"role": "system", "content": (
            "Ты — робот-конфигуратор. Твоя задача — составить список исключений для нейросети. "
            "ИГНОРИРУЙ всё, что не является текстом с кодом или важным конфигом. "
            "ОБЯЗАТЕЛЬНО ИГНОРИРУЙ: .exe, .dll, .pdb, .so, .bin, .cache, .png, .jpg, .ico, .pdf, .zip, .nupkg. "
            "ОСТАВЛЯЙ: .cs, .cpp, .h, .js, .css, .cshtml, .py, .json (только appsettings). "
            "Ответь ТОЛЬКО списком паттернов (например, *.dll), без лишних слов."
        )},
        {"role": "user", "content": stats}
    ]

    res1 = get_groq_completion(prompt1)
    ext_rules = clean_ai_response(res1.choices[0].message.content) if not isinstance(res1, str) else []
    if isinstance(res1, str): return
    ext_ignore_rules = res1.choices[0].message.content.strip()

    # Создаем временный фильтр для дерева
    spec = pathspec.PathSpec.from_lines('gitwildmatch', ext_ignore_rules.splitlines())

    # --- ШАГ 2: Фильтрация по структуре папок (Дерево) ---
    compact_tree = get_optimized_tree(repo_path, spec)

    prompt2 = [
    {"role": "system", "content": (
        "Ты — оптимизатор контекста. Перед тобой дерево папок с оценкой количества токенов. "
        "Твой лимит на весь проект — 100,000 токенов. "
        "Твоя задача: безжалостно выкинуть папки, которые:"
        "1. Содержат внешние библиотеки (даже если они называются не packages/ или node_modules/)."
        "2. Являются артефактами сборки или кэшем."
        "3. Содержат слишком много токенов, но не несут уникальной бизнес-логики (картинки, огромные JSON-даты)."
        "Выдай ТОЛЬКО список паттернов для .aiignore."
    )},
    {"role": "user", "content": compact_tree}
]

    res2 = get_groq_completion(prompt2)
    folder_ignore_rules_list = clean_ai_response(res2.choices[0].message.content) if not isinstance(res2, str) else []

    # --- ФИНАЛ: Сборка файла ---
    all_rules = sorted(list(set(ext_rules + folder_ignore_rules_list)))
    final_content = "# Generated AI Ignore Rules\n" + "\n".join(all_rules)

    tool_dir = repo_path / ".ai_github_tool"
    tool_dir.mkdir(exist_ok=True)
    (tool_dir / ".aiignore").write_text(final_content, encoding="utf-8")

    print(f"[{repo.name}] .aiignore успешно обновлен. Записано правил: {len(all_rules)}")