"""
Download 70 accommodation-style images with no API key and attach them to data.csv.

This uses no-key LoremFlickr image URLs rather than Google Maps scraping.
Images are saved under backend/static/images/pg-listings and data.csv is updated
so each PG points at its own local file.

Usage:
    python scripts/download_pg_images_no_key.py
"""

from __future__ import annotations

import csv
import mimetypes
import re
import shutil
from pathlib import Path
from typing import Dict, Iterable, List
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data.csv"
IMAGES_DIR = PROJECT_ROOT / "backend" / "static" / "images" / "pg-listings"
PUBLIC_IMAGE_PREFIX = "/static/images/pg-listings"

IMAGE_COLUMNS = ["local_image_path", "image_url", "image_source", "image_attribution"]
IMAGE_KEYWORDS = [
    "hostel,room",
    "student,room",
    "dormitory,room",
    "apartment,bedroom",
    "flat,interior",
    "shared,room",
    "guesthouse,room",
    "bedroom,interior",
    "rental,apartment",
    "accommodation,room",
]


def http_download(url: str, path: Path) -> None:
    req = Request(url, headers={"User-Agent": "PGNest-image-downloader/1.0"})
    with urlopen(req, timeout=45) as response:
        content_type = response.headers.get_content_type()
        if not content_type.startswith("image/"):
            raise RuntimeError(f"Not an image: {content_type}")
        with path.open("wb") as handle:
            shutil.copyfileobj(response, handle)


def image_extension(url: str) -> str:
    clean = url.split("?", 1)[0]
    suffix = Path(clean).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    guessed = mimetypes.guess_extension(mimetypes.guess_type(clean)[0] or "")
    return guessed if guessed in {".jpg", ".png", ".webp"} else ".jpg"


def ensure_columns(fieldnames: Iterable[str]) -> List[str]:
    columns = list(fieldnames)
    for column in IMAGE_COLUMNS:
        if column not in columns:
            columns.append(column)
    return columns


def safe_name(pg_id: str, pg_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", pg_name.lower()).strip("-")
    return f"{pg_id.lower()}-{slug[:42]}"


def image_source_url(index: int, row: Dict[str, str]) -> str:
    room_type = (row.get("room_type") or "").strip().lower()
    if room_type == "single":
        keywords = "single,bedroom"
    elif room_type == "double":
        keywords = "shared,bedroom"
    elif room_type == "triple":
        keywords = "hostel,room"
    elif room_type == "dormitory":
        keywords = "dormitory,room"
    else:
        keywords = IMAGE_KEYWORDS[index % len(IMAGE_KEYWORDS)]

    return f"https://loremflickr.com/900/650/{keywords}?lock={1000 + index}"


def write_csv_with_fallback(csv_path: Path, fieldnames: List[str], rows: List[Dict[str, str]]) -> Path:
    try:
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return csv_path
    except PermissionError:
        fallback = csv_path.with_name(f"{csv_path.stem}.with-downloaded-images{csv_path.suffix}")
        with fallback.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return fallback


def main() -> int:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    with CSV_PATH.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise RuntimeError("data.csv has no header")
        fieldnames = ensure_columns(reader.fieldnames)
        rows = list(reader)

    downloaded = 0
    for index, row in enumerate(rows):
        image_url = image_source_url(index, row)
        filename = f"{index + 1:02d}-{safe_name(row.get('pg_id', f'pg{index + 1}'), row.get('pg_name', 'pg'))}.jpg"
        target = IMAGES_DIR / filename
        print(f"Downloading {index + 1:02d}/{len(rows)} -> {filename}")
        http_download(image_url, target)

        public_path = f"{PUBLIC_IMAGE_PREFIX}/{filename}"
        row["local_image_path"] = public_path
        row["image_url"] = public_path
        row["image_source"] = "LoremFlickr"
        row["image_attribution"] = "Downloaded via LoremFlickr no-key image source"
        downloaded += 1

    written_path = write_csv_with_fallback(CSV_PATH, fieldnames, rows)

    print()
    print(f"Downloaded images: {downloaded}")
    print(f"Image folder: {IMAGES_DIR}")
    print(f"CSV written: {written_path}")
    if written_path != CSV_PATH:
        print("data.csv was locked. Close it, then replace it with the generated CSV.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
