"""
Download safe-looking PG/hostel/flat/room images for rows missing local images.

No API key is required. The script uses Openverse's public image search with
`mature=false`, then applies conservative metadata filters before downloading:
- must look accommodation-related from title/tags
- must not contain adult/explicit words
- must not contain people/body terms
- must have reasonable image dimensions and file size

It writes images to backend/static/images/pg-listings and updates data.csv.
If data.csv is locked, it writes data.with-safe-images.csv instead.
"""

from __future__ import annotations

import csv
import json
import argparse
import re
import shutil
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data.csv"
BACKEND_DIR = PROJECT_ROOT / "backend"
IMAGES_DIR = BACKEND_DIR / "static" / "images" / "pg-listings"
PUBLIC_IMAGE_PREFIX = "/static/images/pg-listings"

IMAGE_COLUMNS = ["local_image_path", "image_url", "image_source", "image_source_url", "image_attribution"]

ACCOMMODATION_TERMS = {
    "room", "rooms", "bedroom", "bedrooms", "bed", "beds", "hostel", "hostels",
    "dormitory", "dorm", "apartment", "flat", "interior", "accommodation",
    "guesthouse", "residence", "rental", "housing", "suite", "lodging",
}

REJECT_TERMS = {
    "adult", "xxx", "porn", "porno", "sex", "sexy", "nude", "naked", "nsfw",
    "erotic", "lingerie", "bikini", "underwear", "bra", "breast", "cleavage",
    "fetish", "escort", "strip", "stripper", "onlyfans", "sensual",
    "person", "people", "human", "humans", "man", "men", "woman", "women",
    "girl", "girls", "boy", "boys", "child", "children", "baby", "portrait",
    "face", "selfie", "model", "body", "couple", "family", "wedding",
    "concert", "party", "bar", "beach", "swimwear",
    "bathroom", "bath", "bathtub", "toilet", "sink", "washbasin", "basin",
    "salon", "spa", "office", "workshop", "shop", "store", "restaurant",
    "hall", "auditorium", "theatre", "theater", "palace", "church",
    "chandelier", "wallpaper", "door", "corridor", "staircase", "kitchen",
}

QUERY_BY_ROOM_TYPE = {
    "single": [
        "empty single bedroom interior",
        "small bedroom interior",
        "apartment bedroom interior",
    ],
    "double": [
        "empty twin bedroom interior",
        "shared bedroom interior",
        "hostel room beds",
    ],
    "triple": [
        "hostel room beds",
        "dormitory room beds",
        "student accommodation room",
    ],
    "dormitory": [
        "empty dormitory room beds",
        "hostel dorm room beds",
        "bunk bed room interior",
    ],
}


def http_json(url: str) -> Dict:
    req = Request(url, headers={"User-Agent": "PGNest-safe-image-downloader/1.0"})
    with urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def download_image(url: str, path: Path) -> int:
    req = Request(url, headers={"User-Agent": "PGNest-safe-image-downloader/1.0"})
    with urlopen(req, timeout=45) as response:
        content_type = response.headers.get_content_type()
        if not content_type.startswith("image/"):
            raise RuntimeError(f"not an image response: {content_type}")
        with path.open("wb") as handle:
            shutil.copyfileobj(response, handle)
    return path.stat().st_size


def words_from_text(value: str) -> Set[str]:
    return set(re.findall(r"[a-z]+", (value or "").lower()))


def result_text(result: Dict) -> str:
    tag_names = " ".join(tag.get("name", "") for tag in result.get("tags", []) if isinstance(tag, dict))
    return " ".join([
        str(result.get("title") or ""),
        str(result.get("url") or ""),
        str(result.get("creator") or ""),
        str(result.get("attribution") or ""),
        tag_names,
    ]).lower()


def title_tag_text(result: Dict) -> str:
    tag_names = " ".join(tag.get("name", "") for tag in result.get("tags", []) if isinstance(tag, dict))
    return " ".join([
        str(result.get("title") or ""),
        tag_names,
    ]).lower()


def is_safe_accommodation_result(result: Dict) -> bool:
    if result.get("mature") is True:
        return False

    width = int(result.get("width") or 0)
    height = int(result.get("height") or 0)
    if width < 500 or height < 350:
        return False

    filetype = (result.get("filetype") or "").lower()
    if filetype and filetype not in {"jpg", "jpeg", "png", "webp"}:
        return False

    text = result_text(result)
    all_words = words_from_text(text)
    title_tag_words = words_from_text(title_tag_text(result))
    if all_words & REJECT_TERMS:
        return False

    return bool(title_tag_words & ACCOMMODATION_TERMS)


def openverse_search(query: str, page: int) -> List[Dict]:
    params = urlencode({
        "q": query,
        "category": "photograph",
        "extension": "jpg,png,webp",
        "license_type": "all",
        "mature": "false",
        "page_size": 20,
        "page": page,
    })
    data = http_json(f"https://api.openverse.org/v1/images/?{params}")
    return data.get("results", [])


def candidate_queries(row: Dict[str, str]) -> List[str]:
    room_type = (row.get("room_type") or "").strip().lower()
    queries = list(QUERY_BY_ROOM_TYPE.get(room_type, []))
    queries.extend([
        "empty hostel room beds",
        "empty apartment bedroom interior",
        "guest house room interior",
        "student accommodation bedroom",
    ])
    return queries


def safe_name(pg_id: str, pg_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (pg_name or "pg").lower()).strip("-")
    return f"{(pg_id or 'pg').lower()}-{slug[:42]}"


def local_path_exists(public_path: str) -> bool:
    if not public_path:
        return False
    relative = public_path.replace("/static/", "static/", 1).replace("/", "\\")
    return (BACKEND_DIR / relative).exists()


def ensure_columns(fieldnames: Iterable[str]) -> List[str]:
    columns = list(fieldnames)
    for column in IMAGE_COLUMNS:
        if column not in columns:
            columns.append(column)
    return columns


def find_missing_rows(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return [row for row in rows if not local_path_exists(row.get("local_image_path", ""))]


def already_used_urls(rows: List[Dict[str, str]]) -> Set[str]:
    return {row.get("image_source_url", "") for row in rows if row.get("image_source_url")}


def download_for_row(row: Dict[str, str], index: int, used_urls: Set[str]) -> Optional[Dict[str, str]]:
    for query in candidate_queries(row):
        for page in range(1, 5):
            print(f"  search: {query} page {page}")
            try:
                results = openverse_search(query, page)
            except Exception as exc:
                print(f"    search failed: {exc}")
                time.sleep(1)
                continue

            for result in results:
                url = result.get("url") or result.get("thumbnail")
                if not url or url in used_urls:
                    continue
                if not is_safe_accommodation_result(result):
                    continue

                filename = f"{index:02d}-{safe_name(row.get('pg_id', ''), row.get('pg_name', ''))}.jpg"
                target = IMAGES_DIR / filename
                try:
                    size = download_image(url, target)
                    if size < 12_000:
                        target.unlink(missing_ok=True)
                        print("    rejected tiny file")
                        continue
                except Exception as exc:
                    print(f"    download failed: {exc}")
                    target.unlink(missing_ok=True)
                    continue

                used_urls.add(url)
                return {
                    "public_path": f"{PUBLIC_IMAGE_PREFIX}/{filename}",
                    "source": result.get("provider", "Openverse"),
                    "source_url": result.get("foreign_landing_url", url),
                    "attribution": result.get("attribution", "Openverse image result"),
                }
            time.sleep(0.35)
    return None


def write_csv(csv_path: Path, fieldnames: List[str], rows: List[Dict[str, str]]) -> Path:
    try:
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return csv_path
    except PermissionError:
        fallback_path = csv_path.with_name(f"{csv_path.stem}.with-safe-images{csv_path.suffix}")
        with fallback_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return fallback_path


def selected_rows(rows: List[Dict[str, str]], replace_pg_ids: List[str]) -> List[Dict[str, str]]:
    if not replace_pg_ids:
        return find_missing_rows(rows)
    replace_set = {pg_id.upper() for pg_id in replace_pg_ids}
    return [row for row in rows if (row.get("pg_id") or "").upper() in replace_set]


def main() -> int:
    parser = argparse.ArgumentParser(description="Download safe local PG listing images.")
    parser.add_argument(
        "--replace-pg",
        nargs="*",
        default=[],
        help="PG IDs to replace even if they already have an image, e.g. --replace-pg PG017 PG020",
    )
    args = parser.parse_args()

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    with CSV_PATH.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise RuntimeError("data.csv has no header")
        fieldnames = ensure_columns(reader.fieldnames)
        rows = list(reader)

    missing = selected_rows(rows, args.replace_pg)
    label = "Selected rows" if args.replace_pg else "Missing local images"
    print(f"{label}: {len(missing)}")

    used_urls = already_used_urls(rows)
    filled = 0
    for row in missing:
        row_index = rows.index(row) + 1
        print(f"Downloading image for {row.get('pg_id')} {row.get('pg_name')}")
        image = download_for_row(row, row_index, used_urls)
        if not image:
            print("  no safe image found")
            continue

        row["local_image_path"] = image["public_path"]
        row["image_url"] = image["public_path"]
        row["image_source"] = f"Openverse/{image['source']}"
        row["image_attribution"] = image["attribution"]
        row["image_source_url"] = image["source_url"]
        filled += 1

    written_path = write_csv(CSV_PATH, fieldnames, rows)
    print()
    print(f"Filled rows: {filled}/{len(missing)}")
    print(f"Image folder: {IMAGES_DIR}")
    print(f"CSV written: {written_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
