from __future__ import annotations

import unittest

from src.fuel_retail_price_tracker_latvia.utils import ScrapeError
from src.fuel_retail_price_tracker_latvia.validation import validate_brand_records


def make_row(fuel_code: str, *, price: float = 1.75, address: str = "Rīga") -> dict:
    return {
        "timestamp": "2026-09-17T09:00+03:00",
        "country": "LV",
        "brand": "Circle K",
        "fuel_code": fuel_code,
        "fuel_name_raw": fuel_code,
        "price_eur_l": price,
        "dus_address": address,
        "source_url": "https://example.test/prices",
        "note": "",
    }


class ValidationTests(unittest.TestCase):
    def test_accepts_complete_plausible_source_output(self) -> None:
        rows = [
            make_row("E95", address="Station 1"),
            make_row("E98", address="Station 1"),
            make_row("DD", address="Station 1"),
        ]
        validate_brand_records("Circle K", rows)

    def test_rejects_promotional_text_as_address(self) -> None:
        rows = [
            make_row("E95", address="0,04€ par katru litru"),
            make_row("E98", address="Station 1"),
            make_row("DD", address="Station 1"),
        ]
        with self.assertRaisesRegex(ScrapeError, "promotional text"):
            validate_brand_records("Circle K", rows)

    def test_rejects_implausible_price(self) -> None:
        rows = [
            make_row("E95", price=5.55, address="Station 1"),
            make_row("E98", address="Station 1"),
            make_row("DD", address="Station 1"),
        ]
        with self.assertRaisesRegex(ScrapeError, "outside"):
            validate_brand_records("Circle K", rows)

    def test_rejects_missing_required_fuel(self) -> None:
        rows = [
            make_row("E95", address="Station 1"),
            make_row("DD", address="Station 1"),
        ]
        with self.assertRaisesRegex(ScrapeError, "missing required fuel codes: E98"):
            validate_brand_records("Circle K", rows)

    def test_rejects_empty_source_output(self) -> None:
        with self.assertRaisesRegex(ScrapeError, "returned no rows"):
            validate_brand_records("Circle K", [])


if __name__ == "__main__":
    unittest.main()
