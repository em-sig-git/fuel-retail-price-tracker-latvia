from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.fuel_retail_price_tracker_latvia import main
from src.fuel_retail_price_tracker_latvia.models import FuelRecord
from src.fuel_retail_price_tracker_latvia.utils import ScrapeError


class SuccessfulCircleKScraper:
    brand = "Circle K"

    def __init__(self, session: object) -> None:
        self.session = session

    def scrape(self, timestamp: str) -> list[FuelRecord]:
        return [
            FuelRecord(
                timestamp=timestamp,
                country="LV",
                brand=self.brand,
                fuel_code=fuel_code,
                fuel_name_raw=fuel_code,
                price_eur_l=1.75,
                dus_address="Station 1",
                source_url="https://example.test/prices",
            )
            for fuel_code in ("E95", "E98", "DD")
        ]


class FailedVirsiScraper:
    brand = "Virši"

    def __init__(self, session: object) -> None:
        self.session = session

    def scrape(self, timestamp: str) -> list[FuelRecord]:
        raise RuntimeError("source unavailable")


class MainPolicyTests(unittest.TestCase):
    def test_saves_successful_sources_when_another_source_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            with (
                patch.object(
                    main,
                    "LATVIA_SCRAPERS",
                    [SuccessfulCircleKScraper, FailedVirsiScraper],
                ),
                patch.object(main, "DATA_DIR", state_dir / "data"),
                patch.object(main, "LOG_DIR", state_dir / "logs"),
                patch.object(main, "setup_logging"),
                patch.object(
                    main,
                    "timestamp_now_iso",
                    return_value="2026-09-17T09:00+03:00",
                ),
                patch.object(main, "merge_and_save") as merge_and_save,
            ):
                self.assertEqual(main.run(), 0)

        saved_frame = merge_and_save.call_args.args[0]
        self.assertEqual(set(saved_frame["brand"]), {"Circle K"})
        self.assertEqual(len(saved_frame), 3)

    def test_fails_without_saving_when_every_source_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            with (
                patch.object(main, "LATVIA_SCRAPERS", [FailedVirsiScraper]),
                patch.object(main, "DATA_DIR", state_dir / "data"),
                patch.object(main, "LOG_DIR", state_dir / "logs"),
                patch.object(main, "setup_logging"),
                patch.object(main, "merge_and_save") as merge_and_save,
            ):
                with self.assertRaisesRegex(ScrapeError, "No valid rows"):
                    main.run()

        merge_and_save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
