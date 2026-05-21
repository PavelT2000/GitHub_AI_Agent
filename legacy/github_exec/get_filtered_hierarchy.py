import os
from pathlib import Path
import pathspec
from my_repo import MyRepo

def get_filtered_hierarchy(repo: MyRepo) -> str:
    """
    Возвращает иерархию файлов репозитория, исключая те, 
    что указаны в .ai_github_tool/.aiignore.
    """
    project_root = Path.cwd()
    repo_path = project_root / "temp" / repo.name
    ignore_file = repo_path / ".ai_github_tool" / ".aiignore"

    if not repo_path.exists():
        return "Ошибка: Репозиторий не найден локально."

    # 1. Загружаем правила из .aiignore
    if ignore_file.exists():
        with open(ignore_file, 'r', encoding='utf-8') as f:
            spec = pathspec.PathSpec.from_lines('gitwildmatch', f)
    else:
        # Если файла нет, ничего не игнорируем (кроме .git)
        spec = pathspec.PathSpec.from_lines('gitwildmatch', [])

    filtered_files = []

    # 2. Обходим дерево файлов
    for root, dirs, files in os.walk(repo_path):
        # Убираем .git из обхода сразу
        if '.git' in dirs:
            dirs.remove('.git')
        if '.ai_github_tool' in dirs:
            dirs.remove('.ai_github_tool')

        for file in files:
            full_path = Path(root) / file
            # Получаем путь относительно корня репозитория для проверки
            relative_path = full_path.relative_to(repo_path)
            
            # 3. Проверяем, подходит ли файл под правила игнорирования
            if not spec.match_file(str(relative_path)):
                filtered_files.append(str(relative_path))

    return "\n".join(sorted(filtered_files))