
from pathlib import Path
from git import Repo as GitRepo
from my_repo import MyRepo

def download_repository(repo: MyRepo, token: str):
    """
    Скачивает репозиторий и обновляет флаг downloaded в объекте MyRepo.
    """
    project_root = Path.cwd()
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