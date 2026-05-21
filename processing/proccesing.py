from my_repo import MyRepo
from config import settings
from github import Github
from pathlib import Path
from git import Repo as GitRepo
import pathspec
from my_groq import get_groq_completion, clean_ai_response
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
    spec = pathspec.PathSpec.from_lines('gitwildmatch', ext_ignore_rules.splitlines())
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
    all_rules = sorted(list(set(ext_rules + folder_ignore_rules_list)))
    final_content = "# Generated AI Ignore Rules\n" + "\n".join(all_rules)
    tool_dir = repo_path / ".ai_github_tool"
    tool_dir.mkdir(exist_ok=True)
    (tool_dir / ".aiignore").write_text(final_content, encoding="utf-8")
    print(f"[{repo.name}] .aiignore успешно обновлен. Записано правил: {len(all_rules)}")
    repo.ai_ignore=True
    

def get_repo_information(repo: MyRepo):
    raise NotImplementedError()