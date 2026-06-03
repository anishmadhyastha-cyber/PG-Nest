"""
Populate PGNest CSV image fields.

This script does not scrape Google Maps pages. It uses place_id values already
present in verification_link, and can optionally resolve remaining search links
through the official Google Places API when GOOGLE_MAPS_API_KEY is configured.

Usage:
    python scripts/populate_pg_images.py
    python scripts/populate_pg_images.py --csv data.csv --resolve-missing
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.parse import quote_plus, urlencode, urlparse, parse_qs
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = PROJECT_ROOT / "data.csv"
PLACE_ID_RE = re.compile(r"place_id:([^&\s]+)")

IMAGE_COLUMNS = [
    "google_place_id",
    "google_maps_url",
    "image_url",
    "image_source",
    "image_attribution",
]

ROOM_FALLBACKS = {
    "single": "/static/images/single.png",
    "double": "/static/images/double.png",
    "triple": "/static/images/triple.png",
    "dormitory": "/static/images/double.png",
}


def extract_place_id(verification_link: str) -> str:
    match = PLACE_ID_RE.search(verification_link or "")
    return match.group(1) if match else ""


def build_maps_url(name: str, address: str, place_id: str) -> str:
    query = quote_plus(f"{name} {address}".strip())
    if place_id:
        return (
            "https://www.google.com/maps/search/"
            f"?api=1&query={query}&query_place_id={quote_plus(place_id)}"
        )
    return f"https://www.google.com/maps/search/?api=1&query={query}"


def fallback_image_for_room(room_type: str) -> str:
    return ROOM_FALLBACKS.get((room_type or "").strip().lower(), "/static/images/double.png")


def google_get_json(url: str) -> Dict:
    req = Request(url, headers={"User-Agent": "PGNest-image-populator/1.0"})
    with urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def resolve_place_id(row: Dict[str, str], api_key: str) -> str:
    query = f"{row.get('pg_name', '')} {row.get('full_address', '')} Bengaluru".strip()
    params = urlencode(
        {
            "query": query,
            "fields": "place_id,name,formatted_address",
            "key": api_key,
        }
    )
    data = google_get_json(f"https://maps.googleapis.com/maps/api/place/findplacefromtext/json?inputtype=textquery&input={quote_plus(query)}&fields=place_id,name,formatted_address&key={quote_plus(api_key)}")
    candidates = data.get("candidates") or []
    if not candidates:
        return ""
    return candidates[0].get("place_id", "")


def proxy_photo_url(place_id: str) -> str:
    return f"/api/place-photo/{place_id}" if place_id else ""


def ensure_columns(fieldnames: Iterable[str]) -> List[str]:
    columns = list(fieldnames)
    for column in IMAGE_COLUMNS:
        if column not in columns:
            columns.append(column)
    return columns


def populate(csv_path: Path, resolve_missing: bool, delay_seconds: float) -> Dict[str, int]:
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    if resolve_missing and not api_key:
        raise RuntimeError("Set GOOGLE_MAPS_API_KEY before using --resolve-missing.")

    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise RuntimeError(f"No CSV header found in {csv_path}")
        fieldnames = ensure_columns(reader.fieldnames)
        rows = list(reader)

    stats = {
        "rows": len(rows),
        "place_id_from_csv": 0,
        "place_id_resolved": 0,
        "google_proxy_images": 0,
        "fallback_images": 0,
    }

    for row in rows:
        place_id = row.get("google_place_id", "").strip()
        if not place_id:
            place_id = extract_place_id(row.get("verification_link", ""))
            if place_id:
                stats["place_id_from_csv"] += 1

        if not place_id and resolve_missing:
            try:
                place_id = resolve_place_id(row, api_key)
                if place_id:
                    stats["place_id_resolved"] += 1
                time.sleep(delay_seconds)
            except Exception as exc:
                print(f"[WARN] Could not resolve {row.get('pg_id')} {row.get('pg_name')}: {exc}")

        row["google_place_id"] = place_id
        row["google_maps_url"] = build_maps_url(
            row.get("pg_name", ""),
            row.get("full_address", ""),
            place_id,
        )

        if place_id:
            row["image_url"] = proxy_photo_url(place_id)
            row["image_source"] = "Google Places API"
            row["image_attribution"] = "See Google Places photo attribution response"
            stats["google_proxy_images"] += 1
        else:
            row["image_url"] = row.get("local_image_path", "") or fallback_image_for_room(row.get("room_type", ""))
            row["image_source"] = "Local fallback"
            row["image_attribution"] = ""
            stats["fallback_images"] += 1

    try:
        write_csv(csv_path, fieldnames, rows)
    except PermissionError:
        fallback_path = csv_path.with_name(f"{csv_path.stem}.with-images{csv_path.suffix}")
        write_csv(fallback_path, fieldnames, rows)
        stats["wrote_fallback_file"] = str(fallback_path)

    return stats


def write_csv(csv_path: Path, fieldnames: List[str], rows: List[Dict[str, str]]) -> None:
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Populate PGNest data.csv image columns.")
    parser.add_argument("--csv", default=str(DEFAULT_CSV), help="Path to data.csv")
    parser.add_argument(
        "--resolve-missing",
        action="store_true",
        help="Use GOOGLE_MAPS_API_KEY to resolve search-query rows into place_id values.",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=0.15,
        help="Delay between Google Places resolve requests.",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv).resolve()
    stats = populate(csv_path, args.resolve_missing, args.delay_seconds)
    print("Updated image fields:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    if "wrote_fallback_file" in stats:
        print()
        print("Could not overwrite the original CSV because Windows locked it.")
        print("Close data.csv in VS Code/Excel/Notepad, then run:")
        print(f"  Move-Item -LiteralPath '{stats['wrote_fallback_file']}' -Destination '{csv_path}' -Force")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
