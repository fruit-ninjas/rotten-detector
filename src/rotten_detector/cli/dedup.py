import sys
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from rotten_detector.dedup.md5 import md5_of
from rotten_detector.dedup.phash import group_by, phash_of

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
DEDUP_OPERATIONS = ("md5", "phash", "embedding")


def img_path_iterator(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        suffix = path.suffix.lower()
        if path.is_file() and suffix in IMAGE_EXT and not path.name.startswith("."):
            yield path


def scan_md5(root: Path) -> list[list[Path]]:
    def _md5_digest(path: Path) -> str:
        with path.open("rb") as stream:
            return md5_of(stream)

    paths = img_path_iterator(root)
    buckets: dict[str, list[Path]] = defaultdict(list)

    for path in paths:
        try:
            buckets[_md5_digest(path)].append(path)
        except OSError:
            print(f"skip {show(path, root)}", file=sys.stderr)

    return [group for group in buckets.values() if len(group) > 1]


def scan_phash(root: Path, threshold: int = 2) -> list[list[Path]]:
    root_images = list(img_path_iterator(root))
    coded: list[tuple[Path, int]] = []
    
    for path in root_images:
        try:
            with path.open("rb") as stream:
                digest = phash_of(stream)
        except OSError:
            print(f"skip {show(path, root)}", file=sys.stderr)
            continue
        coded.append((path, digest))

    return group_by(coded, threshold)


def scan_embedding(root: Path, threshold: float = 0.98) -> list[list[Path]]:
    raise NotImplementedError()


def show(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def print_groups(operation: str, root: Path, groups: list[list[Path]]) -> None:
    print(f"{operation}: {len(groups)}")
    for index, group in enumerate(groups, start=1):
        print(f"\n[{index}] {len(group)}")
        for path in group:
            print(f"  {show(path, root)}")


def main() -> None:
    if len(sys.argv) < 3 or sys.argv[1] not in DEDUP_OPERATIONS:
        raise SystemExit("usage: rotten-dedup <md5|phash|embedding> DIR")

    operation = sys.argv[1]
    root = Path(sys.argv[2])
    if operation == "md5":
        groups = scan_md5(root)
    elif operation == "phash":
        groups = scan_phash(root)
    else:
        groups = scan_embedding(root)

    print_groups(operation, root, groups)
