from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
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


@patch.dict("os.environ", {"GITHUB_ACTIONS": "false", "GITHUB_OUTPUT": ""})
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


class BrandNotificationTests(unittest.TestCase):
    watched_brands = ("Circle K", "Viada", "Virši")

    def test_reports_every_combination_of_missing_watched_brands(self) -> None:
        for mask in range(8):
            successful = [
                brand for index, brand in enumerate(self.watched_brands)
                if mask & (1 << index)
            ]
            expected_missing = sorted(set(self.watched_brands) - set(successful))
            with self.subTest(successful=successful), tempfile.TemporaryDirectory() as directory:
                output_path = Path(directory) / "github-output"
                stdout = io.StringIO()
                with (
                    patch.dict("os.environ", {
                        "GITHUB_ACTIONS": "true",
                        "GITHUB_OUTPUT": str(output_path),
                    }),
                    redirect_stdout(stdout),
                ):
                    actual = main.report_missing_brands(successful + ["Latvijas Nafta"])
                self.assertEqual(actual, expected_missing)
                self.assertEqual(
                    output_path.read_text(encoding="utf-8"),
                    f"missing_brands={', '.join(expected_missing)}\n",
                )
                if expected_missing:
                    self.assertIn("::warning title=Missing fuel price data::", stdout.getvalue())
                    self.assertIn(", ".join(expected_missing), stdout.getvalue())
                else:
                    self.assertEqual(stdout.getvalue(), "")
                self.assertNotIn("Latvijas Nafta", stdout.getvalue())

    def test_does_not_emit_github_commands_outside_actions(self) -> None:
        stdout = io.StringIO()
        with (
            patch.dict("os.environ", {"GITHUB_ACTIONS": "false", "GITHUB_OUTPUT": ""}),
            redirect_stdout(stdout),
        ):
            self.assertEqual(
                main.report_missing_brands([]),
                ["Circle K", "Viada", "Virši"],
            )
        self.assertEqual(stdout.getvalue(), "")

    def test_partial_runs_still_save_and_return_success_before_workflow_check(self) -> None:
        brands = (*self.watched_brands, "Latvijas Nafta")
        scenarios = [
            {"Circle K"}, {"Viada"}, {"Virši"}, {"Latvijas Nafta"},
            set(self.watched_brands),
        ]

        def scraper_for(brand, failed):
            class FakeScraper:
                def __init__(self, session):
                    self.session = session

                def scrape(self, timestamp):
                    if failed:
                        return []
                    fuels = ("Ecto-95", "E98", "DD") if brand == "Viada" else ("E95", "E98", "DD")
                    return [
                        FuelRecord(
                            timestamp=timestamp,
                            country="LV",
                            brand=brand,
                            fuel_code=fuel,
                            fuel_name_raw=fuel,
                            price_eur_l=1.75,
                            dus_address="Station 1",
                            source_url="https://example.test/prices",
                        )
                        for fuel in fuels
                    ]
            FakeScraper.brand = brand
            return FakeScraper

        for failed in scenarios:
            with self.subTest(failed=failed), tempfile.TemporaryDirectory() as directory:
                state_dir = Path(directory)
                output_path = state_dir / "github-output"
                stdout = io.StringIO()
                with (
                    patch.dict("os.environ", {
                        "GITHUB_ACTIONS": "true",
                        "GITHUB_OUTPUT": str(output_path),
                    }),
                    patch.object(main, "LATVIA_SCRAPERS", [
                        scraper_for(brand, brand in failed) for brand in brands
                    ]),
                    patch.object(main, "DATA_DIR", state_dir / "data"),
                    patch.object(main, "LOG_DIR", state_dir / "logs"),
                    patch.object(main, "setup_logging"),
                    patch.object(main, "merge_and_save") as merge_and_save,
                    redirect_stdout(stdout),
                ):
                    self.assertEqual(main.run(), 0)
                merge_and_save.assert_called_once()
                saved = merge_and_save.call_args.args[0]
                self.assertEqual(set(saved["brand"]), set(brands) - failed)
                expected_missing = sorted(set(self.watched_brands) & failed)
                self.assertEqual(
                    output_path.read_text(encoding="utf-8"),
                    f"missing_brands={', '.join(expected_missing)}\n",
                )
                self.assertEqual("::warning" in stdout.getvalue(), bool(expected_missing))
                self.assertNotIn("Latvijas Nafta", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
