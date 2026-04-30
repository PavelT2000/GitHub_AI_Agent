import os
from github import Github, Repository
from pathlib import Path
from git import Repo as GitRepo
from my_repo import MyRepo

def get_all_repositories(token: str) -> list[MyRepo]:
    """
    Возвращает список объектов MyRepo с установленным флагом downloaded.
    """
    g = Github(token.strip())
    project_root = Path(__file__).parent
    temp_dir = project_root / "temp"

    # Получаем список из API
    raw_repos = g.get_user().get_repos(type="all")

    my_repos = []
    for r in raw_repos:
        # Оборачиваем в наш класс
        repo_obj = MyRepo(r)

        # Проверяем наличие в папке temp
        repo_path = temp_dir / repo_obj.name
        if repo_path.exists() and any(repo_path.iterdir()):
            repo_obj.downloaded = True

        my_repos.append(repo_obj)

    return my_repos

def download_repository(repo: MyRepo, token: str):
    """
    Скачивает репозиторий и обновляет флаг downloaded в объекте MyRepo.
    """
    project_root = Path(__file__).parent
    temp_dir = project_root / "temp"
    download_path = temp_dir / repo.name

    temp_dir.mkdir(exist_ok=True)

    if repo.downloaded:
        return f"Репозиторий {repo.name} уже помечен как скачанный."

    print(f"--- Начинаю загрузку: {repo.full_name} ---")

    clean_token = token.strip()
    # Используем clone_url из базового класса Repository
    clone_url = repo.clone_url.replace("https://", f"https://{clean_token}@")

    try:
        if download_path.exists() and any(download_path.iterdir()):
            repo.downloaded = True
            return f"Папка {repo.name} уже существует. Статус обновлен."

        # Реальное скачивание
        GitRepo.clone_from(clone_url, download_path)

        # Устанавливаем флаг в нашем кастомном поле
        repo.downloaded = True
        return f"Успешно: {repo.name} скачан в temp/"

    except Exception as e:
        repo.downloaded = False
        return f"Ошибка при скачивании {repo.name}: {e}"

def setup_aiignore(repo: MyRepo):
    """
    Создает конфиг .aiignore в папке .ai_github_tool внутри скачанного репозитория.
    Если репозиторий не скачан, вызывает ошибку.
    """
    # 1. Проверка флага скачивания
    if not repo.downloaded:
        raise RuntimeError(f"Ошибка: Репозиторий '{repo.name}' еще не скачан! Сначала вызовите download_repository.")

    # 2. Определяем пути (внутри папки temp/название_репо)
    project_root = Path(__file__).parent
    repo_path = project_root / "temp" / repo.name
    tool_dir = repo_path / ".ai_github_tool"
    ignore_file = tool_dir / ".aiignore"

    try:
        # 3. Создаем структуру внутри репозитория
        tool_dir.mkdir(parents=True, exist_ok=True)

        if not ignore_file.exists():
            ignore_file.write_text("not implemented", encoding="utf-8")
            print(f"[{repo.name}] Файл .aiignore успешно создан.")
        else:
            print(f"[{repo.name}] Конфигурация уже существует.")

    except Exception as e:
        print(f"Ошибка при работе с файловой системой для {repo.name}: {e}")