import os
from pathlib import Path
import pathspec
from collections import Counter
from my_repo import MyRepo


def get_optimized_tree(repo_path: Path, spec: pathspec.PathSpec, max_files_per_type=5) -> str:
    tree_lines = []

    def build(current_path: Path, prefix="", level=0):
        # 1. Сбор элементов (как и раньше)
        valid_items = []
        try:
            items = sorted(list(current_path.iterdir()), key=lambda x: (x.is_file(), x.name))
            for item in items:
                if '.git' in item.parts or '.ai_github_tool' in item.parts:
                    continue
                if not spec.match_file(str(item.relative_to(repo_path))):
                    valid_items.append(item)
        except Exception:
            return

        if not valid_items:
            return

        dirs = [i for i in valid_items if i.is_dir()]
        files = [i for i in valid_items if i.is_file()]

        folder_size_chars = sum(f.stat().st_size for f in current_path.rglob('*') if f.is_file())
        est_tokens = folder_size_chars // 4
        # 2. ЛОГИКА СХЛОПЫВАНИЯ:
        # Если в папке только одна подпапка и НЕТ файлов — копим путь в префикс
        if len(dirs) == 1 and len(files) == 0:
            child_dir = dirs[0]
            # Добавляем имя текущей папки в префикс для следующего шага
            new_prefix = f"{prefix}{current_path.name}/"
            build(child_dir, new_prefix, level) # level НЕ увеличиваем, так как строку еще не печатали
            return

        # 3. ПЕЧАТЬ:
        # Теперь вычисляем отступ на основе уровня вложенности
        indent = "  " * level
        display_name = f"{prefix}{current_path.name}/"
        tree_lines.append(f"{indent}{display_name} (~{est_tokens} tokens)")

        # Для детей увеличиваем уровень отступа
        for d in dirs:
            build(d, "", level + 1) # Префикс сбрасываем, так как ветка отрисована

        # Вывод файлов с правильным отступом
        file_indent = "  " * (level + 1)
        if files:
            from collections import Counter
            ext_counts = Counter(f.suffix.lower() for f in files)
            processed_exts = set()
            for f in files:
                ext = f.suffix.lower()
                if ext_counts[ext] > max_files_per_type:
                    if ext not in processed_exts:
                        tree_lines.append(f"{file_indent}[{ext_counts[ext]} files: *{ext}]")
                        processed_exts.add(ext)
                else:
                    tree_lines.append(f"{file_indent}{f.name}")

    # Запуск от корня (корень обычно не схлопываем для ясности)
    # Но если нужно схлопнуть и корень — вызываем build(repo_path)
    # Для красоты структуры начнем обход содержимого корня:
    try:
        items = sorted(list(repo_path.iterdir()), key=lambda x: (x.is_file(), x.name))
        for item in items:
            if '.git' in item.parts or '.ai_github_tool' in item.parts:
                continue
            if not spec.match_file(str(item.relative_to(repo_path))):
                if item.is_dir():
                    build(item, "", 0)
                else:
                    tree_lines.append(f"{item.name}")
    except Exception as e:
        return f"Error: {e}"

    return "\n".join(tree_lines)


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