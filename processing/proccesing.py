from my_repo import MyRepo
from config import settings
from github import Github
from pathlib import Path
from git import Repo as GitRepo
import pathspec
from open_ai_module import get_ai_completion, count_tokens
from .utils import (
    get_optimized_tree,
    get_repo_extensions,
    build_files_registry,
    format_files_for_selection,
    resolve_selected_path,
)


def get_all_repositories() -> list[MyRepo]:
    """
    Возвращает список объектов MyRepo с установленным флагом downloaded.
    """
    github = Github(settings.GITHUB_TOKEN.strip())
    project_root = Path.cwd()
    temp_dir = project_root / "temp"
    raw_repos = github.get_user().get_repos(type="all")
    my_repos = []
    for repo in raw_repos:
        repo_obj = MyRepo(repo)
        repo_path = temp_dir / repo_obj.name
        if repo_path.exists() and any(repo_path.iterdir()):
            repo_obj.downloaded = True
        my_repos.append(repo_obj)
    return my_repos

def download_repository(repo: MyRepo, github_token: str | None = None):
    """
    Скачивает репозиторий и обновляет флаг downloaded в объекте MyRepo.
    """
    project_root = Path.cwd()
    temp_dir = project_root / "temp"
    download_path = temp_dir / repo.name
    temp_dir.mkdir(exist_ok=True)
    if repo.downloaded:
        return f"Репозиторий {repo.name} уже помечен как скачанный."
    clean_token = (github_token or settings.GITHUB_TOKEN).strip()
    if not clean_token:
        raise ValueError("GitHub token не указан: передайте token или задайте GITHUB_TOKEN в .env")
    clone_url = repo.clone_url.replace("https://", f"https://{clean_token}@")
    if download_path.exists() and any(download_path.iterdir()):
        repo.downloaded = True
    GitRepo.clone_from(clone_url, download_path)
    repo.downloaded = True
    return f"Успешно: {repo.name} скачан в temp/"

def setup_aiignore(repo: MyRepo):
    """
    Двухэтапный алгоритм генерации правил игнорирования.
    """
    project_root = Path.cwd()
    repo_path = project_root / "temp" / repo.name
    stats = get_repo_extensions(repo_path)
    prompt1 = [
    {"role": "system", "content": (
        "You are a strict code context optimizer. Analyze the provided directory tree and token counts.\n"
        "Your goal is to generate .aiignore patterns to exclude build artifacts, cache, generated code, and heavy non-business assets, while retaining project structure.\n\n"
        "CRITICAL RULES:\n"
        "1. ALWAYS IGNORE: Build and IDE folders (.vs/, bin/, obj/, .git/, .idea/).\n"
        "2. ALWAYS IGNORE heavy text data, assets, and binaries: *.txt, *.log, *.dll, *.exe, *.pdb, *.cache, *.png, *.jpg, *.zip.\n"
        "3. ALWAYS IGNORE automatically generated UI code and resources: *.Designer.cs, *.resx.\n"
        "4. NEVER IGNORE critical project structure and config files: DO NOT ignore *.csproj, *.sln, *.json, .gitignore.\n"
        "5. KEEP source code files intact (*.cs, *.py, *.js).\n\n"
        "OUTPUT FORMAT:\n"
        "Output ONLY valid wildcard patterns (one per line). Strictly NO explanations, NO markdown formatting, NO introduction, NO bullet points. Just raw text patterns."
    )},
    {"role": "user", "content": (
        "Project/\n"
        "  .vs/ (~15000 tokens)\n"
        "  bin/Debug/ (~8000 tokens)\n"
        "  src/ (~2000 tokens)"
    )},
    {"role": "assistant", "content": ".vs/\nbin/\nobj/"},
    {"role": "user", "content": stats}
    ]
    res1 = get_ai_completion(prompt1)
    if isinstance(res1, str):
        return
    ext_rules = res1.choices[0].message.content.strip()
    spec = pathspec.PathSpec.from_lines('gitwildmatch', ext_rules.splitlines())
    compact_tree = get_optimized_tree(repo_path, spec)
    prompt2 = [
        {"role": "system", "content": (
            "You are a strict code context optimizer. Analyze the provided directory tree and token counts.\n"
            "Your goal is to generate .aiignore patterns to exclude build artifacts (.vs, bin, obj), cache, binaries, and heavy temporary test files, WHILE KEEPING structural configuration files.\n\n"
            "CRITICAL RULES:\n"
            "1. NEVER IGNORE project structure and build configuration files: DO NOT add *.csproj or *.sln to the ignore list.\n"
            "2. ALWAYS IGNORE build and IDE artifacts: .vs/, bin/, obj/, .git/.\n"
            "3. ALWAYS IGNORE compiled binaries and logs: *.dll, *.exe, *.pdb, *.log, *.cache.\n\n"
            "OUTPUT FORMAT:\n"
            "Output ONLY valid wildcard patterns, one per line. Strictly NO explanations, NO markdown formatting (do not use blocks like ```), NO introduction, and NO bullet points. Just raw text patterns."
        )},
        # Даем ИИ пример (One-Shot), чтобы он понял структуру ответа
        {"role": "user", "content": "Project/\n  .vs/ (~15000 tokens)\n  bin/Debug/ (~8000 tokens)\n  src/ (~2000 tokens)"},
        {"role": "assistant", "content": ".vs/\nbin/\nobj/"},
        # Передаем реальные данные
        {"role": "user", "content": compact_tree}
    ]
    res2 = get_ai_completion(prompt2)
    folder_ignore_rules_list = res2.choices[0].message.content

    # 1. Разбиваем строки на правильные списки по переносу строки
    # и сразу убираем пустые элементы и пробелы по краям
    list_ext = [line.strip() for line in ext_rules.splitlines() if line.strip()]
    list_folder = [line.strip() for line in folder_ignore_rules_list.splitlines() if line.strip()]

    # 2. Объединяем списки, убираем дубликаты через set и сортируем
    all_rules = sorted(list(set(list_ext + list_folder)))

    # 3. Собираем финальный файл
    final_content = "# Generated AI Ignore Rules\n" + "\n".join(all_rules)
    tool_dir = repo_path / ".ai_github_tool"
    tool_dir.mkdir(exist_ok=True)
    (tool_dir / ".aiignore").write_text(final_content, encoding="utf-8")
    print(f"[{repo.name}] .aiignore успешно обновлен. Записано правил: {len(all_rules)}")
    repo.ai_ignore=True


def get_repo_information(repo: MyRepo, token_limit: int = 10000) -> str:
    """
    Анализирует репозиторий, формирует дерево с учетом .aiignore,
    просит ИИ выбрать самые важные файлы под заданный лимит токенов (token_limit)
    и возвращает финальный склеенный контекст проекта для отправки в LLM.
    """
    project_root = Path.cwd()
    repo_path = project_root / "temp" / repo.name

    if not repo_path.exists():
        return f"Ошибка: Репозиторий {repo.name} не скачан локально."

    # 1. Загружаем правила .aiignore
    ignore_file = repo_path / ".ai_github_tool" / ".aiignore"
    ignore_rules = []
    if ignore_file.exists():
        ignore_rules = [
            line for line in ignore_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
    spec = pathspec.PathSpec.from_lines('gitwildmatch', ignore_rules)

    repo_files_registry = build_files_registry(repo_path, spec)

    if not repo_files_registry:
        return (
            f"=== Selected Repository Context for: {repo.name} ===\n"
            "[ВНИМАНИЕ: Нет доступных файлов после фильтрации .aiignore]\n"
            "Total Collected Tokens: ~0"
        )

    files_list = format_files_for_selection(repo_files_registry)

    prompt = [
        {"role": "system", "content": (
            "You are a codebase architect CLI tool. Your task is to select files containing application logic for comprehensive analysis.\n\n"
            f"CRITICAL CONSTRAINT: Select as many relevant files as possible, maximizing information density without exceeding the strict budget of {token_limit} tokens total. Stop adding files only when the next file would violate this limit.\n\n"
            "SELECTION PRIORITY:\n"
            "- High Priority: Source code files (.cs, .py, .js, .ts, .go, etc.), including entry points, services, controllers, models, and UI logic code.\n"
            "- Medium Priority: Project files (*.csproj, *.sln).\n"
            "- DO NOT SELECT: .gitignore, build artifacts, binary assets, or test-only scaffolding unless no source code exists.\n\n"
            "You receive a flat list where each line is a FULL relative path from repository root (POSIX /), followed by (~N tokens).\n"
            "Copy paths EXACTLY as shown — do not shorten or guess nested folders.\n\n"
            "OUTPUT FORMAT RULES:\n"
            "1. Output ONLY a flat list of relative file paths (one per line, use /).\n"
            "2. Strictly NO numbered lists.\n"
            "3. Strictly NO introduction, NO Markdown code blocks, NO conclusion text, and NO human commentary.\n"
            "4. Output must be raw plain text paths only."
        )},
        {"role": "user", "content": (
            "Lab1/Lab1/Program.cs (~125 tokens)\n"
            "Lab1/Lab1/Form1.cs (~3645 tokens)\n"
            "Lab1/Lab1.csproj (~73 tokens)"
        )},
        {"role": "assistant", "content": "Lab1/Lab1/Program.cs\nLab1/Lab1/Form1.cs\nLab1/Lab1.csproj"},
        {"role": "user", "content": files_list},
    ]

    ai_response = get_ai_completion(prompt)
    if isinstance(ai_response, str):
        return f"Ошибка при запросе к ИИ: {ai_response}"

    selected_files_text = ai_response.choices[0].message.content.strip()
    # Чистим возвращенные ИИ пути от возможных Windows-слэшей и пробелов
    selected_files = [line.strip().replace("\\", "/") for line in selected_files_text.splitlines() if line.strip()]

    # 5. Собираем финальный контекст
    final_context = []
    current_total_tokens = 0

    final_context.append(f"=== Selected Repository Context for: {repo.name} ===")
    final_context.append(f"Budget Limit: {token_limit} tokens\n")

    skipped_paths: list[str] = []

    for rel_path_str in selected_files:
        clean_rel_path = rel_path_str.strip("'\" `")
        resolved_path = resolve_selected_path(clean_rel_path, repo_files_registry)
        if not resolved_path:
            skipped_paths.append(clean_rel_path)
            continue

        target_file = repo_path / resolved_path

        if target_file.exists():
            file_tokens = repo_files_registry[resolved_path]

            if current_total_tokens + file_tokens > token_limit:
                final_context.append(
                    f"\n[ВНИМАНИЕ: Сборка остановлена. Следующий файл {resolved_path} превышает лимит в {token_limit} токенов]"
                )
                break

            try:
                content = target_file.read_text(encoding="utf-8", errors="replace")
                final_context.append(f"--- File: {resolved_path} (~{file_tokens} tokens) ---")
                final_context.append(content)
                final_context.append("-" * 40 + "\n")
                current_total_tokens += file_tokens
            except Exception:
                continue

    if skipped_paths:
        final_context.append(
            f"\n[ВНИМАНИЕ: ИИ указал несуществующие пути, пропущено: {', '.join(skipped_paths)}]"
        )

    final_context.append(f"=== End of Context. Total Collected Tokens: ~{current_total_tokens} ===")
    return "\n".join(final_context)

def generate_readme(repo: MyRepo, project_context: str) -> str:
    """
    Генерирует профессиональный файл README.md на основе собранного ИИ контекста проекта.
    """
    prompt = [
        {"role": "system", "content": (
            "You are an expert technical writer and senior software architect.\n"
            "Your task is to analyze the provided source code context and generate a professional, comprehensive README.md for the repository.\n\n"
            "THE README MUST INCLUDE:\n"
            "1. Project Title & Clear Description (What is this project, its purpose, and core problem solved).\n"
            "2. Key Features (Bullet points highlighting main architectural components and business logic).\n"
            "3. Tech Stack (Languages, frameworks, and core dependencies identified from the code).\n"
            "4. Project Structure Overview (Brief technical map of the main modules).\n"
            "5. Getting Started / Basic Usage guide based on the entry points found.\n\n"
            "OUTPUT FORMAT RULES:\n"
            "- Output ONLY valid Markdown content. Do NOT wrap the entire response in ```markdown blocks.\n"
            "- Do NOT write introduction text like 'Here is your README' or concluding remarks.\n"
            "- Keep it highly professional, technical, clean, and developer-friendly."
        )},
        {"role": "user", "content": f"REPOSITORY NAME: {repo.name}\n\nSOURCE CODE CONTEXT:\n{project_context}"}
    ]

    ai_response = get_ai_completion(prompt)
    if isinstance(ai_response, str):
        return f"Ошибка генерации README: {ai_response}"

    readme_content = ai_response.choices[0].message.content.strip()

    # Сохраняем сгенерированный README локально в папку репозитория
    project_root = Path.cwd()
    repo_path = project_root / "temp" / repo.name

    if repo_path.exists():
        tool_dir = repo_path / ".ai_github_tool"
        tool_dir.mkdir(exist_ok=True)
        (tool_dir / "README.md").write_text(readme_content, encoding="utf-8")
        print(f"[{repo.name}] README.md успешно сгенерирован и сохранен в .ai_github_tool/")

    return readme_content