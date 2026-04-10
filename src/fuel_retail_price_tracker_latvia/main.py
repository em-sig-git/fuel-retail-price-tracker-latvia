from __future__ import annotations

import logging

import pandas as pd
import requests

from .config import DATA_DIR, LOG_DIR
from .storage import merge_and_save
from .utils import ScrapeError, as_dataframe, setup_logging, timestamp_now_iso
from .scrapers.latvia import LATVIA_SCRAPERS


def run() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    setup_logging()

    timestamp = timestamp_now_iso()
    logging.info("Scrape session started at %s", timestamp)

    all_rows = []
    session = requests.Session()

    for scraper_cls in LATVIA_SCRAPERS:
        scraper = scraper_cls(session)
        try:
            rows = [record.to_dict() for record in scraper.scrape(timestamp=timestamp)]
            logging.info("%s: %s rows", scraper.brand, len(rows))
            all_rows.extend(rows)
        except Exception as exc:
            logging.exception("%s failed: %s", scraper.brand, exc)

    df_new = as_dataframe(all_rows)
    if df_new.empty:
        raise ScrapeError("No rows scraped from any configured source")

    df_new = df_new.sort_values(by=["brand", "fuel_code", "dus_address"])
    merge_and_save(df_new)

    logging.info("Scrape session finished. New rows: %s", len(df_new))
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
