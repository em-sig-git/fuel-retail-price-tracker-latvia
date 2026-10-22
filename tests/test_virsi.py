from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from src.fuel_retail_price_tracker_latvia.scrapers.latvia import VirsiScraper
from src.fuel_retail_price_tracker_latvia.utils import ScrapeError
from src.fuel_retail_price_tracker_latvia.validation import validate_brand_records


TIMESTAMP = "2026-10-22T09:00+03:00"
PRICE_HTML = """
<html><title>Fuel prices</title>
<div class="price-card"><p class="price"><span>95E</span><span>1.914</span></p><p class="address">Station 1</p></div>
<div class="price-card"><p class="price"><span>98E</span><span>1.984</span></p><p class="address">Station 1</p></div>
<div class="price-card"><p class="price"><span>DD</span><span>2.014</span></p><p class="address">Station 1</p></div>
<div class="price-card"><p class="price"><span>LPG</span><span>1.005</span></p><p class="address">Station 1</p></div>
</html>
"""


def http_error(status: int) -> requests.HTTPError:
    response = requests.Response()
    response.status_code = status
    return requests.HTTPError(f"HTTP {status}", response=response)


class VirsiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scraper = VirsiScraper(Mock(spec=requests.Session))

    def test_working_http_path_does_not_launch_browser(self) -> None:
        with (
            patch("src.fuel_retail_price_tracker_latvia.scrapers.latvia.fetch_html", return_value=PRICE_HTML),
            patch.object(self.scraper, "_fetch_rendered_html") as browser_fetch,
        ):
            rows = list(self.scraper.scrape(TIMESTAMP))
        browser_fetch.assert_not_called()
        self.assertEqual(len(rows), 4)
        validate_brand_records("Virši", [row.to_dict() for row in rows])

    def test_blocked_http_request_uses_rendered_prices(self) -> None:
        for status in (403, 429, 503):
            with self.subTest(status=status):
                with (
                    patch("src.fuel_retail_price_tracker_latvia.scrapers.latvia.fetch_html", side_effect=http_error(status)),
                    patch.object(self.scraper, "_fetch_rendered_html", return_value=PRICE_HTML) as browser_fetch,
                ):
                    rows = list(self.scraper.scrape(TIMESTAMP))
                browser_fetch.assert_called_once()
                self.assertEqual({row.fuel_code for row in rows}, {"E95", "E98", "DD", "LPG"})
                self.assertEqual(next(row.price_eur_l for row in rows if row.fuel_code == "DD"), 2.014)
                self.assertTrue(all(row.timestamp == TIMESTAMP for row in rows))
                validate_brand_records("Virši", [row.to_dict() for row in rows])

    def test_challenge_returned_with_http_200_uses_browser(self) -> None:
        with (
            patch("src.fuel_retail_price_tracker_latvia.scrapers.latvia.fetch_html", return_value="<title>Just a moment...</title>"),
            patch.object(self.scraper, "_fetch_rendered_html", return_value=PRICE_HTML) as browser_fetch,
        ):
            rows = list(self.scraper.scrape(TIMESTAMP))
        browser_fetch.assert_called_once()
        self.assertEqual(len(rows), 4)

    def test_not_found_is_not_hidden_by_browser_retry(self) -> None:
        with (
            patch("src.fuel_retail_price_tracker_latvia.scrapers.latvia.fetch_html", side_effect=http_error(404)),
            patch.object(self.scraper, "_fetch_rendered_html") as browser_fetch,
        ):
            with self.assertRaises(requests.HTTPError):
                list(self.scraper.scrape(TIMESTAMP))
        browser_fetch.assert_not_called()

    def test_failed_browser_does_not_produce_price_records(self) -> None:
        with (
            patch("src.fuel_retail_price_tracker_latvia.scrapers.latvia.fetch_html", side_effect=http_error(403)),
            patch.object(self.scraper, "_fetch_rendered_html", side_effect=ScrapeError("still challenged")),
        ):
            with self.assertRaisesRegex(ScrapeError, "still challenged"):
                list(self.scraper.scrape(TIMESTAMP))

    def test_browser_waits_for_prices_and_is_closed_on_success(self) -> None:
        with patch("playwright.sync_api.sync_playwright") as factory:
            browser = factory.return_value.__enter__.return_value.chromium.launch.return_value
            page = browser.new_page.return_value
            page.content.return_value = PRICE_HTML
            html = self.scraper._fetch_rendered_html()
        self.assertEqual(html, PRICE_HTML)
        page.wait_for_selector.assert_called_once_with(
            ".price-card p.price span:nth-child(2)", state="attached", timeout=45000
        )
        browser.close.assert_called_once()

    def test_browser_timeout_has_context_and_closes_browser(self) -> None:
        with patch("playwright.sync_api.sync_playwright") as factory:
            browser = factory.return_value.__enter__.return_value.chromium.launch.return_value
            page = browser.new_page.return_value
            page.goto.return_value.status = 403
            page.title.return_value = "Just a moment..."
            page.wait_for_selector.side_effect = PlaywrightTimeout("timeout")
            with self.assertRaisesRegex(ScrapeError, "initial HTTP 403"):
                self.scraper._fetch_rendered_html()
        browser.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
