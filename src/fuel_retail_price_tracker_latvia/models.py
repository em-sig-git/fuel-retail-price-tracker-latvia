from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass(frozen=True)
class FuelRecord:
    timestamp: str
    country: str
    brand: str
    fuel_code: str
    fuel_name_raw: str
    price_eur_l: float
    dus_address: str
    source_url: str
    note: str = ""
    scraped_at: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)
