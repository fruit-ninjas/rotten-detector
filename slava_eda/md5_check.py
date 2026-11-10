import hashlib
import sys
from collections import defaultdict
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tiff"}


def md5_of_file(path: Path, chunk_size: int = 1 << 20) -> str:
    """Считает md5 файла потоково (не грузит весь файл в память)."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def iter_images(root: Path):
    """Рекурсивно перебирает файлы-изображения по расширению."""
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            yield p


def find_duplicates(root: Path, follow_symlinks: bool = False):
    """
    Возвращает dict: md5 -> список путей с этим хешем.
    Включает только хеши, встретившиеся >= 2 раз (реальные дубликаты).
    """
    by_hash = defaultdict(list)

    for path in iter_images(root):
        if not follow_symlinks and path.is_symlink():
            continue
        try:
            digest = md5_of_file(path)
        except (OSError, PermissionError) as e:
            print(f"[skip] {path}: {e}", file=sys.stderr)
            continue
        by_hash[digest].append(path)

    return {h: paths for h, paths in by_hash.items() if len(paths) > 1}


def main():
    # Путь можно передать аргументом: python script.py pomidor/good
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("pomidor")

    if not root.is_dir():
        print(f"Не директория: {root}", file=sys.stderr)
        sys.exit(1)

    print(f"Сканирую: {root.resolve()}")

    total_images = 0
    for _ in iter_images(root):
        total_images += 1

    duplicates = find_duplicates(root)

    if not duplicates:
        print(f"Изображений: {total_images}. Дубликатов не найдено.")
        return

    dup_files = sum(len(v) - 1 for v in duplicates.values())  # «лишних» копий
    print(f"Изображений: {total_images}")
    print(f"Групп дубликатов: {len(duplicates)}")
    print(f"Лишних копий (сверх одного экземпляра в группе): {dup_files}\n")

    for i, (digest, paths) in enumerate(sorted(duplicates.items(), key=lambda kv: -len(kv[1])), 1):
        print(f"=== Группа {i} (md5={digest}, файлов={len(paths)}) ===")
        for p in sorted(paths):
            print(f"  {p}")
        print()


if __name__ == "__main__":
    main()