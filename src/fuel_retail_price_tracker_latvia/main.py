from __future__ import annotations

import logging
import os
from collections.abc import Iterable

import pandas as pd
import requests

from .config import DATA_DIR, LOG_DIR
from .scrapers.latvia import LATVIA_SCRAPERS
from .storage import merge_and_save
from .utils import ScrapeError, as_dataframe, setup_logging, timestamp_now_iso
from .validation import validate_brand_records


NOTIFY_BRANDS = frozenset({"Circle K", "Viada", "Virši"})


def report_missing_brands(successful_brands: Iterable[str]) -> list[str]:
    missing_brands = sorted(NOTIFY_BRANDS.difference(successful_brands))
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as output:
            output.write(f"missing_brands={', '.join(missing_brands)}\n")
    if missing_brands and os.environ.get("GITHUB_ACTIONS") == "true":
        print(
            "::warning title=Missing fuel price data::"
            f"No valid records for: {', '.join(missing_brands)}",
            flush=True,
        )
    return missing_brands


def run() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    setup_logging()

    timestamp = timestamp_now_iso()
    logging.info("Scrape session started at %s", timestamp)

    all_rows = []
    successful_brands = []
    failed_brands = []
    session = requests.Session()

    for scraper_cls in LATVIA_SCRAPERS:
        scraper = scraper_cls(session)
        try:
            rows = [record.to_dict() for record in scraper.scrape(timestamp=timestamp)]
            validate_brand_records(scraper.brand, rows)
            logging.info("%s: %s rows", scraper.brand, len(rows))
            all_rows.extend(rows)
            successful_brands.append(scraper.brand)
        except Exception as exc:
            logging.exception("%s failed: %s", scraper.brand, exc)
            failed_brands.append(scraper.brand)

    report_missing_brands(successful_brands)

    df_new = as_dataframe(all_rows)
    if df_new.empty:
        raise ScrapeError("No valid rows scraped from any configured source")

    if failed_brands:
        logging.warning(
            "Partial scrape: saving successful brands %s; failed brands: %s",
            ", ".join(successful_brands),
            ", ".join(failed_brands),
        )

    df_new = df_new.sort_values(by=["brand", "fuel_code", "dus_address"])
    merge_and_save(df_new)

    logging.info("Scrape session finished. New rows: %s", len(df_new))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
