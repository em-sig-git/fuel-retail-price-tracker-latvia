"""Validate live Virši collection without modifying the stored CSV."""
from __future__ import annotations

import json
import logging

import requests

from .scrapers.latvia import VirsiScraper
from .utils import timestamp_now_iso
from .validation import validate_brand_records


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    with requests.Session() as session:
        scraper = VirsiScraper(session)
        rows = [record.to_dict() for record in scraper.scrape(timestamp_now_iso())]
    validate_brand_records("Virši", rows)
    print(f"Verified {len(rows)} live Virši records")
    print(json.dumps(rows, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
