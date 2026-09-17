from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from .utils import ScrapeError


MIN_PRICE_EUR_L = 0.50
MAX_PRICE_EUR_L = 3.00

# These are deliberately minimum sets rather than every product currently sold.
# A run is rejected if a source no longer exposes its core petrol/diesel products.
REQUIRED_FUEL_CODES = {
    "Circle K": {"E95", "E98", "DD"},
    "Virši": {"E95", "E98", "DD"},
    "Viada": {"Ecto-95", "E98", "DD"},
    "Latvijas Nafta": {"E95", "E98", "DD"},
}

PROMOTIONAL_ADDRESS_MARKERS = (
    "€",
    "par katru litru",
    "pirmdien",
    "piektdien",
    "atlaide",
)


def validate_brand_records(brand: str, rows: Sequence[Mapping[str, object]]) -> None:
    """Reject incomplete or implausible source output before it reaches storage."""
    if brand not in REQUIRED_FUEL_CODES:
        raise ScrapeError(f"No validation policy configured for {brand}")
    if not rows:
        raise ScrapeError(f"{brand} returned no rows")

    observed_fuels: set[str] = set()
    seen_records: set[tuple[str, str]] = set()

    for index, row in enumerate(rows, start=1):
        timestamp = str(row.get("timestamp", "")).strip()
        if not timestamp:
            raise ScrapeError(f"{brand} row {index} has an empty timestamp")
        if row.get("country") != "LV":
            raise ScrapeError(f"{brand} row {index} does not have country 'LV'")

        row_brand = str(row.get("brand", ""))
        if row_brand != brand:
            raise ScrapeError(
                f"{brand} row {index} has inconsistent brand {row_brand!r}"
            )

        fuel_code = str(row.get("fuel_code", "")).strip()
        if not fuel_code:
            raise ScrapeError(f"{brand} row {index} has an empty fuel code")
        observed_fuels.add(fuel_code)

        try:
            price = float(row["price_eur_l"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ScrapeError(f"{brand} row {index} has no numeric price") from exc
        if not math.isfinite(price) or not MIN_PRICE_EUR_L <= price <= MAX_PRICE_EUR_L:
            raise ScrapeError(
                f"{brand} row {index} price {price!r} is outside "
                f"{MIN_PRICE_EUR_L:.2f}-{MAX_PRICE_EUR_L:.2f} EUR/L"
            )

        address = str(row.get("dus_address", "")).strip()
        if not address:
            raise ScrapeError(f"{brand} row {index} has an empty address")
        address_lower = address.casefold()
        marker = next(
            (value for value in PROMOTIONAL_ADDRESS_MARKERS if value in address_lower),
            None,
        )
        if marker:
            raise ScrapeError(
                f"{brand} row {index} address contains promotional text {marker!r}"
            )

        source_url = str(row.get("source_url", ""))
        if not source_url.startswith("https://"):
            raise ScrapeError(f"{brand} row {index} has a non-HTTPS source URL")

        record_key = (fuel_code, address)
        if record_key in seen_records:
            raise ScrapeError(
                f"{brand} returned duplicate fuel/address record {record_key!r}"
            )
        seen_records.add(record_key)

    missing_fuels = REQUIRED_FUEL_CODES[brand] - observed_fuels
    if missing_fuels:
        raise ScrapeError(
            f"{brand} is missing required fuel codes: {', '.join(sorted(missing_fuels))}"
        )
