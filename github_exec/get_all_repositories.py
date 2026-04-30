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