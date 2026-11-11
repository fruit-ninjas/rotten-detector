import hashlib
from collections import defaultdict
from pathlib import Path

import imagehash
import numpy as np
import pandas as pd
from PIL import Image
from sklearn.metrics.pairwise import cosine_similarity

DATA = Path(__file__).resolve().parent / "data"
ROOTS = {
    "blueberry": DATA / "blueberry_1444282069",
    "peach": DATA / "peach_ 1444282012",
    "paper": DATA / "paper_ 1444282020",
}
EXT = {".jpg", ".jpeg", ".png", ".webp"}


def collect():
    rows = []
    for fruit, folder in ROOTS.items():
        for path in sorted(folder.rglob("*")):
            if not path.is_file() or path.name.startswith("."):
                continue

            if path.suffix.lower() not in EXT:
                continue

            rows.append(
                {
                    "fruit": fruit,
                    "label": path.relative_to(folder).parts[0],
                    "name": path.name,
                    "path": path,
                }
            )
    return rows


def read_file(row):
    try:
        path = row["path"]
        digest = hashlib.md5(path.read_bytes()).hexdigest()

        with Image.open(path) as image:
            rgb = image.convert("RGB")
            width, height = rgb.size
            phash = int(str(imagehash.phash(rgb)), 16)
    except OSError:
        return None

    row["md5"] = digest
    row["phash"] = phash
    row["width"] = width
    row["height"] = height
    return row


def phash_groups(rows):
    groups = []
    for row in rows:
        close = []
        for group in groups:
            for other in group:
                if (row["phash"] ^ other["phash"]).bit_count() <= 2:
                    close.append(group)
                    break

        if not close:
            groups.append([row])
            continue
        merged = [row]

        for group in close:
            merged.extend(group)
            groups.remove(group)
        groups.append(merged)

    return groups


def copies_in_label(rows):
    found = []

    for (fruit, label), part in pd.DataFrame(rows).groupby(["fruit", "label"]):
        part = part.to_dict("records")
        md5_buckets = defaultdict(list)

        for row in part:
            md5_buckets[row["md5"]].append(row)

        md5_images = sum(len(group) for group in md5_buckets.values() if len(group) > 1)
        near = phash_groups(part)
        phash_images = sum(len(group) for group in near if len(group) > 1)

        found.append(
            {
                "fruit": fruit,
                "label": label,
                "images": len(part),
                "md5_images": md5_images,
                "phash_images": phash_images,
            }
        )
    return found


def both_labels(rows):
    found = []

    frame = pd.DataFrame(rows)

    for fruit, part in frame.groupby("fruit"):
        part = part.to_dict("records")
        buckets = defaultdict(list)

        for row in part:
            buckets[row["md5"]].append(row)

        number = 0
        for group in buckets.values():
            labels = {row["label"] for row in group}
            if "accepted" not in labels or "declined" not in labels:
                continue

            number += 1
            for row in group:
                found.append(
                    {
                        "fruit": fruit,
                        "method": "md5",
                        "group": number,
                        "label": row["label"],
                        "name": row["name"],
                    }
                )

        number = 0
        for group in phash_groups(part):
            labels = {row["label"] for row in group}

            if "accepted" not in labels or "declined" not in labels:
                continue

            number += 1

            for row in group:
                found.append(
                    {
                        "fruit": fruit,
                        "method": "phash",
                        "group": number,
                        "label": row["label"],
                        "name": row["name"],
                    }
                )
    return found


def color_vector(path):
    with Image.open(path) as image:
        small = np.asarray(image.convert("RGB").resize((64, 64)))

    parts = []

    for channel in range(3):
        counts, _ = np.histogram(small[:, :, channel], bins=16, range=(0, 255))
        parts.append(counts.astype(np.float32))

    vector = np.concatenate(parts)
    norm = np.linalg.norm(vector)

    if norm == 0:
        return vector

    return vector / norm


def color_matrix(rows):
    vectors = []
    for row in rows:
        vectors.append(color_vector(row["path"]))

    return np.stack(vectors)


def cosine_table(rows, vectors):
    edges = np.linspace(0, 1, 41)
    width = np.diff(edges)
    found = []
    frame = pd.DataFrame(rows)

    for fruit, part in frame.groupby("fruit"):
        accepted = vectors[part.index[part["label"] == "accepted"].to_numpy()]
        declined = vectors[part.index[part["label"] == "declined"].to_numpy()]
        blocks = {
            "within_accepted": cosine_similarity(accepted)[np.triu_indices(len(accepted), k=1)],
            "within_declined": cosine_similarity(declined)[np.triu_indices(len(declined), k=1)],
            "accepted_vs_declined": cosine_similarity(accepted, declined).ravel(),
        }

        for name, values in blocks.items():
            counts, _ = np.histogram(values, bins=edges)
            density = counts / (counts.sum() * width)

            summary = {
                "pairs": int(len(values)),
                "q05": round(float(np.quantile(values, 0.05)), 3),
                "median": round(float(np.median(values)), 3),
                "q95": round(float(np.quantile(values, 0.95)), 3),
            }

            for left, value in zip(edges[:-1], density):
                found.append(
                    {
                        "fruit": fruit,
                        "relation": name,
                        "bin": round(float(left), 4),
                        "density": round(float(value), 4),
                        **summary,
                    }
                )

    return pd.DataFrame(found)


def main():
    rows = []

    for row in collect():
        ready = read_file(row)
        if ready is not None:
            rows.append(ready)

    print("кадров", len(rows))

    cosine_rows = [row for row in rows if row["label"] in ("accepted", "declined")]
    vectors = color_matrix(cosine_rows)
    cosine = cosine_table(cosine_rows, vectors)

    DATA.mkdir(exist_ok=True)
    images = pd.DataFrame(rows)[["fruit", "label", "width", "height"]]

    images.to_csv(DATA / "images.csv", index=False)

    pd.DataFrame(copies_in_label(rows)).to_csv(DATA / "within.csv", index=False)
    pd.DataFrame(both_labels(rows)).to_csv(DATA / "conflicts.csv", index=False)

    cosine.to_csv(DATA / "cosine.csv", index=False)
    
    print("сохранено в", DATA)


if __name__ == "__main__":
    main()
