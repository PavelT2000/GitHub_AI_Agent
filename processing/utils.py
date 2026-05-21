from pathlib import Path
from collections import Counter
import pathspec


def _estimate_tokens(path: Path) -> int:
    try:
        return path.stat().st_size // 4
    except OSError:
        return 0


def get_optimized_tree(
    repo_path: Path,
    spec: pathspec.PathSpec,
    max_files_per_type: int = 5,
    include_file_tokens: bool = False,
) -> str:
    """Строит дерево каталогов с отступами (имена файлов без полного пути)."""
    tree_lines = []

    def file_line(indent: str, file_path: Path) -> str:
        name = file_path.name
        if include_file_tokens:
            return f"{indent}{name} (~{_estimate_tokens(file_path)} tokens)"
        return f"{indent}{name}"

    def build(current_path: Path, prefix: str = "", level: int = 0) -> None:
        valid_items = []
        try:
            items = sorted(current_path.iterdir(), key=lambda x: (x.is_file(), x.name))
            for item in items:
                if ".git" in item.parts or ".ai_github_tool" in item.parts:
                    continue
                if not spec.match_file(str(item.relative_to(repo_path))):
                    valid_items.append(item)
        except OSError:
            return

        if not valid_items:
            return

        dirs = [i for i in valid_items if i.is_dir()]
        files = [i for i in valid_items if i.is_file()]

        folder_tokens = 0
        for f in current_path.rglob("*"):
            if f.is_file() and not spec.match_file(f.relative_to(repo_path).as_posix()):
                folder_tokens += _estimate_tokens(f)

        if len(dirs) == 1 and not files:
            new_prefix = f"{prefix}{current_path.name}/"
            build(dirs[0], new_prefix, level)
            return

        indent = "  " * level
        display_name = f"{prefix}{current_path.name}/"
        tree_lines.append(f"{indent}{display_name} (~{folder_tokens} tokens)")

        for d in dirs:
            build(d, "", level + 1)

        file_indent = "  " * (level + 1)
        if files:
            ext_counts = Counter(f.suffix.lower() for f in files)
            processed_exts: set[str] = set()
            for f in files:
                ext = f.suffix.lower()
                if ext_counts[ext] > max_files_per_type:
                    if ext not in processed_exts:
                        tree_lines.append(f"{file_indent}[{ext_counts[ext]} files: *{ext}]")
                        processed_exts.add(ext)
                else:
                    tree_lines.append(file_line(file_indent, f))

    try:
        items = sorted(repo_path.iterdir(), key=lambda x: (x.is_file(), x.name))
        for item in items:
            if ".git" in item.parts or ".ai_github_tool" in item.parts:
                continue
            if not spec.match_file(str(item.relative_to(repo_path))):
                if item.is_dir():
                    build(item, "", 0)
                else:
                    tree_lines.append(file_line("", item))
    except OSError as e:
        return f"Error: {e}"

    return "\n".join(tree_lines)


def build_files_registry(repo_path: Path, spec: pathspec.PathSpec) -> dict[str, int]:
    """Реестр относительных путей (POSIX) -> оценка токенов для выбранных ИИ файлов."""
    registry: dict[str, int] = {}
    for path in repo_path.rglob("*"):
        if not path.is_file():
            continue
        if ".git" in path.parts or ".ai_github_tool" in path.parts:
            continue
        rel_path = path.relative_to(repo_path).as_posix()
        if not spec.match_file(rel_path):
            registry[rel_path] = _estimate_tokens(path)
    return registry


def get_repo_extensions(repo_path: Path) -> str:
    """Собирает уникальные расширения и файлы без расширений."""
    extensions: set[str] = set()
    files_no_ext: set[str] = set()
    for path in repo_path.rglob("*"):
        if path.is_file() and ".git" not in path.parts:
            if path.suffix:
                extensions.add(path.suffix.lower())
            else:
                files_no_ext.add(path.name)
    return (
        f"Расширения: {', '.join(sorted(extensions))}\n"
        f"Файлы без расширения: {', '.join(sorted(files_no_ext))}"
    )
