import os
import random
import shutil
from pathlib import Path

LIMIT = 2000
def collect_and_copy(src_root: str, dst_root: str, count: int = 4,
                     seed: int | None = None,
                     image_exts=(".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tiff")):
    """
    Обходит все поддиректории src_root. В каждой поддиректории, где есть изображения,
    случайно выбирает до `count` изображений и копирует в dst_root с именем
    '<имя_директории>_<имя_изображения>'.
    """
    src_root = Path(src_root)
    dst_root = Path(dst_root)
    dst_root.mkdir(parents=True, exist_ok=True)

    if seed is not None:
        random.seed(seed)

    if not src_root.is_dir():
        raise NotADirectoryError(f"Не директория: {src_root}")

    total_copied = 0
    total_dirs = 0

    # os.walk обходит все поддиректории, включая вложенные.
    for dirpath, dirnames, filenames in os.walk(src_root):
        dirpath = Path(dirpath)

        # Только файлы-изображения
        images = [f for f in filenames if f.lower().endswith(image_exts)]
        if not images:
            continue

        total_dirs += 1
        dir_name = dirpath.name  # имя текущей директории

        # Берём не больше count, чем есть
        if count == -1:
            # Берём все изображения (порядок — как в filenames, можно перемешать)
            chosen = images
        else:
            # Берём не больше count, чем есть
            k = min(count, len(images))
            chosen = random.sample(images, k)

        for img_name in chosen:
            src_file = dirpath / img_name
            new_name = f"{dir_name}_{img_name}"
            dst_file = dst_root / new_name

            # На случай коллизии (одинаковые имена папок в разных ветках)
            if dst_file.exists():
                stem = Path(new_name).stem
                suffix = Path(new_name).suffix
                i = 1
                while dst_file.exists():
                    dst_file = dst_root / f"{stem}__{i}{suffix}"
                    i += 1

            shutil.copy2(src_file, dst_file)
            total_copied += 1
            if total_copied == LIMIT:
                break
        if total_copied == LIMIT:
            break

    print(f"Обработано директорий с изображениями: {total_dirs}")
    print(f"Скопировано файлов: {total_copied}")


if __name__ == "__main__":
    SRC = "good_pomidor/images"        # <-- укажите путь с исходными директориями
    DST = "pomidor/good/"   # <-- укажите куда копировать
    COUNT = 1                     # сколько изображений брать из каждой директории

    print('Из: ', SRC)
    print('В: ', DST)
    a = input()
    collect_and_copy(SRC, DST, count=COUNT, seed=42)  # seed можно убрать для настоящей случайности