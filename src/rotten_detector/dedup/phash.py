from collections.abc import Iterable
from pathlib import Path
from typing import BinaryIO

import imagehash
from PIL import Image


def phash_of(stream: BinaryIO) -> int:
    with Image.open(stream) as image:
        return int(str(imagehash.phash(image)), 16)


def hamming(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def group_by(items: Iterable[tuple[Path, int]], threshold: int) -> list[list[Path]]:
    groups: list[list[tuple[Path, int]]] = []

    for item, digest in items:
        close = [
            group
            for group in groups
            if any(hamming(digest, other) <= threshold for _, other in group)
        ]
        
        if not close:
            groups.append([(item, digest)])
            continue
        
        merged = [(item, digest)]
        
        for group in close:
            merged.extend(group)
            groups.remove(group)

        groups.append(merged)
        
    return [[item for item, _ in group] for group in groups if len(group) > 1]
