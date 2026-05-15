from my_repo import MyRepo
from config import settings
from github import Github
from pathlib import Path
from git import Repo as GitRepo

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
    raise NotImplementedError()

def get_repo_information(repo: MyRepo):
    raise NotImplementedError()