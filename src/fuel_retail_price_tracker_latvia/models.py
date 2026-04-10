from __future__ import annotations

from dataclasses import dataclass, asdict


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

    def to_dict(self) -> dict:
        return asdict(self)
