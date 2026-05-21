import os
from pathlib import Path
from my_repo import MyRepo

def get_repo_extensions(repo_path: Path) -> str:
    """Собирает уникальные расширения и файлы без расширений."""
    extensions = set()
    files_no_ext = set()
    for path in repo_path.rglob('*'):
        if path.is_file() and '.git' not in path.parts:
            if path.suffix:
                extensions.add(path.suffix.lower())
            else:
                files_no_ext.add(path.name)
    return f"Расширения: {', '.join(extensions)}\nФайлы без расширения: {', '.join(files_no_ext)}"