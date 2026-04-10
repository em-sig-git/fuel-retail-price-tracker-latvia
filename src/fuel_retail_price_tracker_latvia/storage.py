from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .config import OUTPUT_CSV

DEDUP_KEYS = ["timestamp", "country", "brand", "fuel_code", "dus_address"]
COLUMN_ORDER = [
    "timestamp",
    "country",
    "brand",
    "fuel_code",
    "fuel_name_raw",
    "price_eur_l",
    "dus_address",
    "source_url",
    "note",
]


def load_existing(path: Path = OUTPUT_CSV) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=COLUMN_ORDER)
    return pd.read_csv(path, sep=";", decimal=",", encoding="utf-8-sig")


def merge_and_save(df_new: pd.DataFrame, path: Path = OUTPUT_CSV) -> pd.DataFrame:
    path.parent.mkdir(parents=True, exist_ok=True)
    df_old = load_existing(path)
    df_combined = pd.concat([df_new, df_old], ignore_index=True)
    if df_combined.empty:
        df_combined = pd.DataFrame(columns=COLUMN_ORDER)
    else:
        df_combined = df_combined[COLUMN_ORDER]
        df_combined = df_combined.drop_duplicates(subset=DEDUP_KEYS, keep="first")
        df_combined = df_combined.sort_values(
            by=["timestamp", "brand", "fuel_code", "dus_address"],
            ascending=[False, True, True, True],
        )
    df_combined.to_csv(path, sep=";", decimal=",", index=False, encoding="utf-8-sig")
    logging.info("Saved %s rows to %s", len(df_combined), path)
    return df_combined
