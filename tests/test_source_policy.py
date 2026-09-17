from __future__ import annotations

import unittest

from src.fuel_retail_price_tracker_latvia.scrapers.latvia import LATVIA_SCRAPERS


class SourcePolicyTests(unittest.TestCase):
    def test_neste_and_kool_are_not_active_sources(self) -> None:
        active_brands = {scraper.brand for scraper in LATVIA_SCRAPERS}
        self.assertNotIn("Neste", active_brands)
        self.assertNotIn("KOOL", active_brands)


if __name__ == "__main__":
    unittest.main()
