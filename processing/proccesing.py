from my_repo import MyRepo
from config import settings
from github import Github
from pathlib import Path
from git import Repo as GitRepo
import pathspec
from open_ai_module import get_ai_completion, count_tokens
from .utils import get_optimized_tree, get_repo_extensions


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

def download_repository(repo: MyRepo):
    """
    Скачивает репозиторий и обновляет флаг downloaded в объекте MyRepo.
    """
    project_root = Path.cwd()
    temp_dir = project_root / "temp"
    download_path = temp_dir / repo.name
    temp_dir.mkdir(exist_ok=True)
    if repo.downloaded:
        return f"Репозиторий {repo.name} уже помечен как скачанный."
    clean_token = settings.GITHUB_TOKEN.strip()
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
            "You are an automated environment configurator creating a .aiignore file (standard gitignore syntax).\n"
            "Your task is to analyze the file extensions list and output patterns to IGNORE everything except source code and critical configs.\n\n"
            "CRITICAL RULES:\n"
            "1. ALWAYS ignore binary, assets, and cache: *.exe, *.dll, *.pdb, *.so, *.bin, *.cache, *.png, *.jpg, *.ico, *.pdf, *.zip, *.nupkg.\n"
            "2. ALWAYS keep: *.cs, *.cpp, *.h, *.js, *.css, *.cshtml, *.py.\n"
            "3. For JSON files, ignore all JSON but explicitly allow appsettings by adding these two exact lines:\n"
            "*.json\n"
            "!appsettings.json\n\n"
            "Output ONLY the raw wildcard patterns, one per line. No explanations, no bullet points, no markdown blocks, no human commentary."
        )},
        {"role": "user", "content": stats}
    ]
    res1 = get_ai_completion(prompt1)
    ext_rules = res1.choices[0].message.content
    if isinstance(res1, str): return
    ext_ignore_rules = res1.choices[0].message.content.strip()
    spec = pathspec.PathSpec.from_lines('gitwildmatch', ext_ignore_rules.splitlines())
    compact_tree = get_optimized_tree(repo_path, spec)
    prompt2 = [
        {"role": "system", "content": (
            "You are a strict code context optimizer. Analyze the provided directory tree and token counts.\n"
            "Your goal is to generate .aiignore patterns to exclude build artifacts (.vs, bin, obj), cache, dependencies, and heavy non-business logic folders.\n"
            "CRITICAL: Output ONLY valid wildcard patterns (e.g., .vs/, bin/, *.dll), one per line.\n"
            "Strictly NO explanations, NO markdown formatting (do not use blocks like ```), NO introduction, and NO bullet points. Just raw text patterns."
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
        ignore_rules = ignore_file.read_text(encoding="utf-8").splitlines()
    spec = pathspec.PathSpec.from_lines('gitwildmatch', ignore_rules)

    # 2. Получаем текущее оптимизированное дерево для ИИ
    compact_tree = get_optimized_tree(repo_path, spec)

    # 3. Собираем точную базу данных с принудительным POSIX-форматом слэшей (/)
    repo_files_registry = {}
    for p in repo_path.rglob('*'):
        if p.is_file():
            if '.git' in p.parts or '.ai_github_tool' in p.parts:
                continue

            # .as_posix() превращает Windows слэши \ в прямые /
            relative_posix_str = p.relative_to(repo_path).as_posix()

            # Проверяем фильтр pathspec (он требует прямые слэши)
            if not spec.match_file(relative_posix_str):
                try:
                    file_chars = p.stat().st_size
                    repo_files_registry[relative_posix_str] = file_chars // 4
                except Exception:
                    continue

    if not repo_files_registry:
        return f"=== Selected Repository Context for: {repo.name} ===\n[ВНИМАНИЕ: Нет доступных файлов после фильтрации .aiignore]\nTotal Collected Tokens: ~0"

    # Превращаем реестр в текст для ИИ
    registry_text = "\n".join([f"{path} ({tokens} tokens)" for path, tokens in repo_files_registry.items()])

    # 4. Запрос к ИИ
    prompt = [
        {"role": "system", "content": (
            "You are a strict codebase architect CLI tool. Your task is to select the most critical project files for logic analysis.\n\n"
            f"CRITICAL CONSTRAINT: The total token weight of selected files MUST NOT exceed {token_limit} tokens.\n"
            "Select only core business logic files (entry points, controllers, services, models, data contexts).\n"
            "Ignore tests, build artifacts, migrations, and UI assets.\n\n"
            "OUTPUT FORMAT RULES:\n"
            "1. Output ONLY a flat list of relative file paths (one path per line).\n"
            "2. Strictly NO numbered lists (do not use 1, 2, 3).\n"
            "3. Strictly NO introduction, NO Markdown code blocks, NO conclusion text, and NO human commentary.\n"
            "4. Output must be raw plain text paths only."
        )},
        {"role": "user", "content": (
            "STRUCTURE:\nFolder/App.cs (~4000 tokens)\nFolder/Test.cs (~2000 tokens)\n"
            "FILES REGISTRY WITH WEIGHTS:\nFolder/App.cs (4000 tokens)\nFolder/Test.cs (2000 tokens)"
        )},
        {"role": "assistant", "content": "Folder/App.cs"},
        {"role": "user", "content": (
            f"STRUCTURE:\n{compact_tree}\n\n"
            f"FILES REGISTRY WITH WEIGHTS:\n{registry_text}"
        )}
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

    for rel_path_str in selected_files:
        clean_rel_path = rel_path_str.strip("'\" ")
        # Для работы с диском Python Path сам поймет прямые слэши на любой ОС
        target_file = repo_path / clean_rel_path

        if clean_rel_path in repo_files_registry and target_file.exists():
            file_tokens = repo_files_registry[clean_rel_path]

            if current_total_tokens + file_tokens > token_limit:
                final_context.append(f"\n[ВНИМАНИЕ: Сборка остановлена. Следующий файл {clean_rel_path} превышает лимит в {token_limit} токенов]")
                break

            try:
                content = target_file.read_text(encoding="utf-8", errors="replace")
                final_context.append(f"--- File: {clean_rel_path} (~{file_tokens} tokens) ---")
                final_context.append(content)
                final_context.append("-" * 40 + "\n")
                current_total_tokens += file_tokens
            except Exception:
                continue

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