"""Сервис для работы с GitHub API и локальными копиями."""
from pathlib import Path
from github import Github
from git import Repo as GitRepo
from my_repo import MyRepo

def get_all_repositories(token: str) -> list[MyRepo]:
    """Получает список всех репозиториев пользователя."""
    client = Github(token.strip())
    temp_dir = Path.cwd() / "temp"
    
    repos = []
    for raw_repo in client.get_user().get_repos(type="all"):
        repo_obj = MyRepo(raw_repo)
        repo_path = temp_dir / repo_obj.name
        if repo_path.exists() and any(repo_path.iterdir()):
            repo_obj.downloaded = True
        repos.append(repo_obj)
    return repos

def download_repository(repo: MyRepo, token: str) -> str:
    """Клонирует репозиторий в локальную папку."""
    download_path = Path.cwd() / "temp" / repo.name
    download_path.parent.mkdir(exist_ok=True)

    if repo.downloaded:
        return f"Репозиторий {repo.name} уже скачан."

    clone_url = repo.clone_url.replace("https://", f"https://{token.strip()}@")
    try:
        GitRepo.clone_from(clone_url, download_path)
        repo.downloaded = True
        return f"Успешно: {repo.name} скачан."
    except Exception as err:
        return f"Ошибка: {err}"