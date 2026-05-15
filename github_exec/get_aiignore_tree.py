import os
from pathlib import Path
import pathspec
from my_repo import MyRepo

def get_aiignore_tree(repo: MyRepo) -> str:
    """
    Генерирует дерево файлов на основе локального .aiignore.
    Принимает только объект MyRepo.
    """
    project_root = Path.cwd()
    repo_path = project_root / "temp" / repo.name
    ignore_file = repo_path / ".ai_github_tool" / ".aiignore"

    if not repo_path.exists():
        return "Ошибка: Репозиторий не найден локально."

    # 1. ЗАГРУЗКА ПРАВИЛ ИЗ .aiignore
    if ignore_file.exists():
        try:
            with open(ignore_file, 'r', encoding='utf-8') as f:
                # Читаем правила и создаем фильтр spec[cite: 4, 5]
                spec = pathspec.PathSpec.from_lines('gitwildmatch', f.readlines())
        except Exception as e:
            print(f"Ошибка чтения .aiignore: {e}")
            spec = pathspec.PathSpec.from_lines('gitwildmatch', [])
    else:
        # Если файла нет, создаем пустой фильтр
        spec = pathspec.PathSpec.from_lines('gitwildmatch', [])

    tree_lines = []

    def build(current_path: Path, prefix="", level=0):
        valid_items = []
        try:
            # Сортировка: папки выше файлов[cite: 6]
            items = sorted(list(current_path.iterdir()), key=lambda x: (x.is_file(), x.name))
            for item in items:
                # Базовый игнор служебных папок
                if item.name in ['.git', '.ai_github_tool']:
                    continue

                # Проверка по загруженному spec[cite: 5]
                relative_path = item.relative_to(repo_path)
                if not spec.match_file(str(relative_path)):
                    valid_items.append(item)
        except Exception:
            return

        if not valid_items:
            return

        dirs = [i for i in valid_items if i.is_dir()]
        files = [i for i in valid_items if i.is_file()]

        # Расчет токенов для всей папки
        try:
            total_size = sum(f.stat().st_size for f in current_path.rglob('*') if f.is_file())
            folder_tokens = total_size // 4
        except:
            folder_tokens = 0

        # --- PATH COMPRESSION (Схлопывание пустых родителей)[cite: 6] ---
        if len(dirs) == 1 and len(files) == 0:
            child_dir = dirs[0]
            new_prefix = f"{prefix}{current_path.name}/"
            build(child_dir, new_prefix, level)
            return

        # --- ОТРИСОВКА ПАПКИ ---
        indent = "  " * level
        display_name = f"{prefix}{current_path.name}/"
        tree_lines.append(f"{indent}{display_name} (~{folder_tokens} tokens)")

        # Рекурсия для подпапок
        for d in dirs:
            build(d, "", level + 1)

        # --- ОТРИСОВКА ФАЙЛОВ (БЕЗ СХЛОПЫВАНИЯ)[cite: 6] ---
        file_indent = "  " * (level + 1)
        for f in files:
            try:
                f_tokens = f.stat().st_size // 4
                tree_lines.append(f"{file_indent}{f.name} ({f_tokens} tks)")
            except:
                tree_lines.append(f"{file_indent}{f.name}")

    # Запуск сборки от корня
    try:
        # Обрабатываем первый уровень отдельно для красоты вывода
        items = sorted(list(repo_path.iterdir()), key=lambda x: (x.is_file(), x.name))
        for item in items:
            if item.name in ['.git', '.ai_github_tool']:
                continue

            relative_path = item.relative_to(repo_path)
            if not spec.match_file(str(relative_path)):
                if item.is_dir():
                    build(item, "", 0)
                else:
                    f_tokens = item.stat().st_size // 4
                    tree_lines.append(f"{item.name} ({f_tokens} tks)")
    except Exception as e:
        return f"Ошибка построения дерева: {e}"

    return "\n".join(tree_lines)