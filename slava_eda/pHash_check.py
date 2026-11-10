import sys
from collections import defaultdict
from pathlib import Path

import imagehash
from PIL import Image

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tiff"}


def phash_of_file(path: Path, hash_size: int = 8) -> imagehash.ImageHash | None:
    """Считает pHash изображения. Возвращает None, если файл не читается."""
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")  # pHash работает с яркостью, RGB безопасно
            return imagehash.phash(im, hash_size=hash_size)
    except Exception as e:
        print(f"[skip] {path}: {e}", file=sys.stderr)
        return None


def iter_images(root: Path):
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            yield p


def find_similar(root: Path, threshold: int = 5, hash_size: int = 8,
                 follow_symlinks: bool = False):
    """
    Ищет похожие изображения по pHash.

    threshold — максимальное расстояние Хэмминга, при котором два хеша
    считаются «похожими». 0 = идентичные хеши, больше = мягче.
    Для hash_size=8 (64-битный хеш) типичные значения: 0–5 (строго),
    5–10 (средне), 10–15 (мягко, много ложных срабатываний).

    Возвращает список групп: каждая группа — список путей, попарно
    связанных (транзитивное замыкание через union-find).
    """
    if threshold < 0:
        raise ValueError("threshold должен быть >= 0")
    if hash_size < 1:
        raise ValueError("hash_size должен быть >= 1")

    # 1. Считаем хеши
    items: list[tuple[Path, imagehash.ImageHash]] = []
    for path in iter_images(root):
        if not follow_symlinks and path.is_symlink():
            continue
        h = phash_of_file(path, hash_size=hash_size)
        if h is not None:
            items.append((path, h))

    n = len(items)
    if n == 0:
        return [], 0

    # 2. Union-Find: объединяем файлы, у которых расстояние <= threshold.
    #    O(n^2) попарных сравнений — для десятков тысяч это долго;
    #    для умеренных объёмов (до ~5–10k) приемлемо.
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(n):
        hi = items[i][1]
        for j in range(i + 1, n):
            hj = items[j][1]
            if hi - hj <= threshold:  # imagehash поддерживает вычитание -> расстояние Хэмминга
                union(i, j)

    # 3. Группируем по корню union-find
    groups: dict[int, list[Path]] = defaultdict(list)
    for i in range(n):
        groups[find(i)].append(items[i][0])

    # Оставляем только группы из >= 2 файлов
    result = [sorted(g) for g in groups.values() if len(g) > 1]
    # Сортируем группы по размеру (крупные сверху), затем по первому пути
    result.sort(key=lambda g: (-len(g), str(g[0])))
    return result, n


def main():
    # Использование:
    #   python script.py <dir> [threshold] [hash_size]
    # Примеры:
    #   python script.py pomidor/good 5
    #   python script.py pomidor 8 8
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("pomidor")
    threshold = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    hash_size = 8

    if not root.is_dir():
        print(f"Не директория: {root}", file=sys.stderr)
        sys.exit(1)

    print(f"Сканирую: {root.resolve()}")
    print(f"pHash: hash_size={hash_size} ({hash_size*hash_size} бит), "
          f"threshold={threshold} (макс. расстояние Хэмминга)\n")

    groups, total = find_similar(root, threshold=threshold, hash_size=hash_size)

    if not groups:
        print(f"Изображений обработано: {total}. Похожих групп не найдено.")
        return

    extra = sum(len(g) - 1 for g in groups)
    print(f"Изображений обработано: {total}")
    print(f"Групп похожих: {len(groups)}")
    print(f"Лишних копий (сверх одного экземпляра в группе): {extra}\n")

    for i, group in enumerate(groups, 1):
        print(f"=== Группа {i} (файлов={len(group)}) ===")
        for p in group:
            print(f"  {p}")
        print()


if __name__ == "__main__":
    main()