from __future__ import annotations

from pathlib import Path
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
OUTPUT_CSV = DATA_DIR / "fuel_prices_latvia.csv"
LOG_FILE = LOG_DIR / "scrape_history.log"
TIMEZONE = ZoneInfo("Europe/Riga")
COUNTRY = "LV"
