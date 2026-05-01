import os
from pathlib import Path
import pathspec
from collections import Counter

def get_optimized_tree(repo_path: Path, spec: pathspec.PathSpec, max_files_per_type=5) -> str:
    """
    Генерирует максимально сжатое дерево файлов для экономии токенов.
    """
    tree_lines = []

    def build(current_path: Path, indent=""):
        # Получаем список всех элементов, которые не игнорируются
        valid_items = []
        for item in current_path.iterdir():
            if '.git' in item.parts or '.ai_github_tool' in item.parts:
                continue
            if not spec.match_file(str(item.relative_to(repo_path))):
                valid_items.append(item)

        if not valid_items:
            return

        # --- ОПТИМИЗАЦИЯ 1: Схлопывание вложенных папок (Path Compression) ---
        # Если в папке только одна подпапка и нет файлов, объединяем пути
        if len(valid_items) == 1 and valid_items[0].is_dir():
            child = valid_items[0]
            # Рекурсивно тянем имя, пока не найдем ветвление
            return build(child, f"{indent}{current_path.name}/{child.name}")

        # Добавляем текущую директорию (если это не корень)
        if indent == "":
            tree_lines.append(f"{current_path.name}/")
            indent = "  "
        else:
            # Если путь был схлопнут, он придет уже с именем
            if "/" not in indent:
                tree_lines.append(f"{indent}{current_path.name}/")
                indent += "  "

        # Разделяем на файлы и папки
        dirs = [i for i in valid_items if i.is_dir()]
        files = [i for i in valid_items if i.is_file()]

        # Сначала обрабатываем папки
        for d in sorted(dirs):
            build(d, indent)

        # --- ОПТИМИЗАЦИЯ 2: Группировка файлов по расширениям ---
        if files:
            ext_counts = Counter(f.suffix.lower() for f in files)
            processed_exts = set()

            for f in sorted(files, key=lambda x: x.name):
                ext = f.suffix.lower()
                
                # Если файлов такого типа слишком много, группируем их
                if ext_counts[ext] > max_files_per_type:
                    if ext not in processed_exts:
                        tree_lines.append(f"{indent}[{ext_counts[ext]} files: *{ext}]")
                        processed_exts.add(ext)
                else:
                    tree_lines.append(f"{indent}{f.name}")

    # Запускаем сборку от корня
    # Мы не передаем indent в первый вызов, чтобы корень обработался красиво
    try:
        # Для корня немного другая логика, чтобы не печатать полный путь системы
        items = sorted(list(repo_path.iterdir()), key=lambda x: (x.is_file(), x.name))
        for item in items:
            if '.git' in item.parts or '.ai_github_tool' in item.parts:
                continue
            if not spec.match_file(str(item.relative_to(repo_path))):
                if item.is_dir():
                    build(item, "  ")
                else:
                    tree_lines.append(f"  {item.name}")
    except Exception as e:
        return f"Error building tree: {e}"

    return "\n".join(tree_lines)