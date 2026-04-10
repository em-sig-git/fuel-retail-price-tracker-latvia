from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Iterable, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .config import LOG_FILE, TIMEZONE


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def setup_logging() -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


class ScrapeError(RuntimeError):
    pass


def fetch_html(url: str, *, session: requests.Session, timeout: int = 45) -> str:
    response = session.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    return response.text


def soupify(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def now_riga() -> datetime:
    return datetime.now(TIMEZONE)


def timestamp_now_iso() -> str:
    return now_riga().replace(second=0, microsecond=0).isoformat(timespec="minutes")


def extract_first_decimal(text: str) -> Optional[float]:
    if not text:
        return None
    match = re.search(r"(\d+[\.,]\d+)", text)
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def clean_text(text: str) -> str:
    text = text.replace("\xa0", " ").replace("\u200b", " ").replace("\ufeff", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_multiline_text(text: str) -> str:
    text = text.replace("\xa0", " ").replace("\u200b", " ").replace("\ufeff", " ")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def normalize_address(text: str) -> str:
    text = clean_text(text)
    text = text.strip(" ,;.")
    return text


def as_dataframe(records: Iterable[dict]) -> pd.DataFrame:
    df = pd.DataFrame(list(records))
    if df.empty:
        return df
    df["price_eur_l"] = pd.to_numeric(df["price_eur_l"], errors="coerce")
    df = df.dropna(subset=["price_eur_l"])
    return df
