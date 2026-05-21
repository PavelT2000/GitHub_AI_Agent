from pathlib import Path
from urllib.parse import urlparse

from github import Github

from config import settings
from my_repo import MyRepo
from processing import (
    download_repository,
    generate_readme,
    get_repo_information,
    setup_aiignore,
)


def _parse_github_url(url: str) -> tuple[str, str]:
    """Извлекает owner и repo_name из URL GitHub."""
    parsed = urlparse(url.strip())
    path = parsed.path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = [p for p in path.split("/") if p]
    if len(parts) < 2:
        raise ValueError(f"Некорректный URL репозитория: {url}")
    return parts[0], parts[1]


def _resolve_github_token(token: str | None) -> str:
    github_token = (token or settings.GITHUB_TOKEN).strip()
    if not github_token:
        raise ValueError(
            "GitHub token не указан: передайте аргумент token или задайте GITHUB_TOKEN в .env"
        )
    return github_token


def _get_repo(url: str, github_token: str) -> MyRepo:
    owner, repo_name = _parse_github_url(url)
    github = Github(github_token)
    repo = MyRepo(github.get_repo(f"{owner}/{repo_name}"))

    repo_path = Path.cwd() / "temp" / repo.name
    if repo_path.exists() and any(repo_path.iterdir()):
        repo.downloaded = True
    return repo


def get_readme(url: str, token: str | None = None) -> str:
    """
    Скачивает репозиторий по URL, генерирует .aiignore, собирает контекст и создаёт README.md.

    :param url: URL репозитория на GitHub (https://github.com/owner/repo)
    :param token: Опциональный GitHub token; если не передан — берётся из .env
    :return: Содержимое сгенерированного README.md
    """
    github_token = _resolve_github_token(token)
    repo = _get_repo(url, github_token)

    download_repository(repo, github_token=github_token)
    setup_aiignore(repo)

    context = get_repo_information(repo, token_limit=settings.MAX_TOKENS)
    return generate_readme(repo, context)
