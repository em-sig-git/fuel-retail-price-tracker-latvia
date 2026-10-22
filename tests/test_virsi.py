from __future__ import annotations

import unittest
from unittest.mock import Mock

import requests

from src.fuel_retail_price_tracker_latvia.scrapers.latvia import VirsiScraper
from src.fuel_retail_price_tracker_latvia.utils import ScrapeError


TIMESTAMP = "2026-10-22T09:00+03:00"


def price_page(*, fuels=("95E", "98E", "DD", "LPG"), title="Degvielas cenas Latvijā | Virši"):
    cards = "".join(
        f'<div class="price-card"><p class="price"><span>{fuel}</span>'
        '<span>1,750</span></p><p class="address">Visā Viršu tīklā</p></div>'
        for fuel in fuels
    )
    return f'<html lang="lv"><head><title>{title}</title></head><body>{cards}</body></html>'


def response(html: str, *, status: int = 200) -> requests.Response:
    result = requests.Response()
    result.status_code = status
    result._content = html.encode("utf-8")
    result.encoding = "utf-8"
    return result


class VirsiTests(unittest.TestCase):
    def setUp(self):
        self.session = Mock(spec=requests.Session)
        self.scraper = VirsiScraper(self.session)

    def test_uses_primary_without_requesting_alternate(self):
        self.session.get.return_value = response(price_page())
        records = list(self.scraper.scrape(TIMESTAMP))
        self.assertEqual(len(records), 4)
        self.assertEqual({row.fuel_code for row in records}, {"E95", "E98", "DD", "LPG"})
        self.assertEqual({row.source_url for row in records}, {self.scraper.source_url})
        self.session.get.assert_called_once()

    def test_403_uses_official_alternate_and_records_actual_source(self):
        self.session.get.side_effect = [response("challenge", status=403), response(price_page())]
        records = list(self.scraper.scrape(TIMESTAMP))
        self.assertEqual(len(records), 4)
        self.assertEqual({row.source_url for row in records}, {self.scraper.fallback_url})
        self.assertEqual({row.country for row in records}, {"LV"})
        self.assertEqual({row.dus_address for row in records}, {"Visā Viršu tīklā"})
        self.assertEqual({row.price_eur_l for row in records}, {1.75})
        self.assertEqual(
            [call.args[0] for call in self.session.get.call_args_list],
            [self.scraper.source_url, self.scraper.fallback_url],
        )

    def test_200_challenge_page_also_uses_alternate(self):
        self.session.get.side_effect = [
            response("<title>Mazliet uzgaidiet...</title>"), response(price_page())
        ]
        records = list(self.scraper.scrape(TIMESTAMP))
        self.assertEqual({row.source_url for row in records}, {self.scraper.fallback_url})

    def test_incomplete_primary_is_replaced_with_complete_alternate(self):
        self.session.get.side_effect = [
            response(price_page(fuels=("95E", "DD"))), response(price_page())
        ]
        records = list(self.scraper.scrape(TIMESTAMP))
        self.assertEqual(len(records), 4)
        self.assertEqual({row.source_url for row in records}, {self.scraper.fallback_url})

    def test_connection_failure_uses_alternate(self):
        self.session.get.side_effect = [requests.Timeout("timed out"), response(price_page())]
        self.assertEqual(len(list(self.scraper.scrape(TIMESTAMP))), 4)

    def test_rejects_alternate_page_for_another_country(self):
        self.session.get.side_effect = [
            response("challenge", status=403),
            response(price_page(title="Degalų kainos Lietuvoje | Virši")),
        ]
        with self.assertRaisesRegex(ScrapeError, "did not return the Latvian price page"):
            list(self.scraper.scrape(TIMESTAMP))

    def test_both_sources_failing_raises_instead_of_returning_partial_rows(self):
        self.session.get.side_effect = [
            response("challenge", status=403), response(price_page(fuels=("95E",)))
        ]
        with self.assertRaisesRegex(ScrapeError, "missing required fuel codes"):
            list(self.scraper.scrape(TIMESTAMP))


if __name__ == "__main__":
    unittest.main()
