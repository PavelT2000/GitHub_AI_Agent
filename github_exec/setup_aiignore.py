from pathlib import Path
from my_repo import MyRepo

def setup_aiignore(repo: MyRepo):
    """
    Создает конфиг .aiignore в папке .ai_github_tool внутри скачанного репозитория.
    Если репозиторий не скачан, вызывает ошибку.
    """
    # 1. Проверка флага скачивания
    if not repo.downloaded:
        raise RuntimeError(f"Ошибка: Репозиторий '{repo.name}' еще не скачан! Сначала вызовите download_repository.")

    # 2. Определяем пути (внутри папки temp/название_репо)
    project_root = Path.cwd()
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