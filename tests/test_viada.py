from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import requests

from src.fuel_retail_price_tracker_latvia.scrapers.latvia import ViadaScraper
from src.fuel_retail_price_tracker_latvia.utils import ScrapeError
from src.fuel_retail_price_tracker_latvia.validation import validate_brand_records


FETCH_HTML = "src.fuel_retail_price_tracker_latvia.scrapers.latvia.fetch_html"
CHALLENGE_HTML = (
    "<html><title>One moment, please...</title>"
    "<body>Please wait while your request is being verified...</body></html>"
)


def fuel_row(label: str, price: str, stations: list[tuple[str, str]]) -> str:
    items = "".join(
        f'<li><span><a class="fuel-table__station" href="/dus/example/">{name}</a>'
        f'<span class="fuel-table__address">{address}</span></span></li>'
        for name, address in stations
    )
    return (
        '<div class="fuel-table__row"><div class="fuel-table__fuel">'
        f'<img src="/new-icon.png" alt=""><span>{label}</span></div>'
        f'<p class="fuel-table__price">{price} <span>EUR / L</span></p>'
        f'<ul class="fuel-table__stations">{items}</ul></div>'
    )


def api_response(html: str, **overrides) -> str:
    payload = {
        "id": 8830,
        "link": ViadaScraper.source_url,
        "slug": "zemakas-degvielas-cenas",
        "content": {"rendered": html},
    }
    payload.update(overrides)
    return json.dumps(payload)


class ViadaTests(unittest.TestCase):
    def scrape(self, html: str):
        with requests.Session() as session, patch(FETCH_HTML, return_value=html):
            return list(ViadaScraper(session).scrape("2026-11-13T08:27+02:00"))

    def test_new_page_keeps_the_seven_price_series_separate(self) -> None:
        ulmana = ("ADUS Ulmaņa", "Kārļa Ulmaņa gatve 67, Rīga")
        bikernieku = ("ADUS Biķernieku", "Vecā Biķernieku iela 1, Rīga")
        darzciema = ("DUS Dārzciema", "Dārzciema iela 69, Rīga")
        saharova = ("ADUS Saharova", "Andreja Saharova iela 10, Rīga")
        astras = ("DUS Astras", "G.Astras iela 7, Rīga")
        html = '<div class="fuel-table">' + "".join([
            fuel_row("95 Multi FX", "1.737", [ulmana, bikernieku]),
            fuel_row("95 Multi FX plus", "1.762", [bikernieku]),
            fuel_row("98 Multi FX", "1.842", [ulmana, bikernieku]),
            fuel_row("D", "2.054", [darzciema]),
            fuel_row("D Multi FX", "1.957", [ulmana, saharova]),
            fuel_row("Gāze", "1.045", [saharova]),
            fuel_row("E85", "1.995", [astras]),
        ]) + "</div>"

        rows = self.scrape(html)
        validate_brand_records("Viada", [row.to_dict() for row in rows])
        self.assertEqual(
            [(row.fuel_code, row.fuel_name_raw, row.price_eur_l) for row in rows],
            [
                ("Ecto-95", "95 Multi FX", 1.737),
                ("Ecto-95+", "95 Multi FX plus", 1.762),
                ("E98", "98 Multi FX", 1.842),
                ("DD", "D", 2.054),
                ("Ecto-DD", "D Multi FX", 1.957),
                ("LPG", "Gāze", 1.045),
                ("E85", "E85", 1.995),
            ],
        )
        self.assertEqual(
            rows[0].dus_address,
            "ADUS Ulmaņa : Kārļa Ulmaņa gatve 67, Rīga, "
            "ADUS Biķernieku : Vecā Biķernieku iela 1, Rīga",
        )
        self.assertEqual(rows[1].dus_address, "ADUS Biķernieku : Vecā Biķernieku iela 1, Rīga")
        self.assertEqual(rows[3].dus_address, "DUS Dārzciema : Dārzciema iela 69, Rīga")

    def test_missing_station_address_rejects_an_incomplete_price_row(self) -> None:
        html = '<div class="fuel-table">' + fuel_row("D", "2.054", [
            ("DUS Dārzciema", "Dārzciema iela 69, Rīga"),
            ("DUS Dārzciema 2", ""),
        ]) + "</div>"
        with self.assertRaisesRegex(ScrapeError, "incomplete station for D"):
            self.scrape(html)

    def test_old_table_still_parses_the_icon_based_fuel_code(self) -> None:
        rows = self.scrape("""
            <table><tr><td><img src="/uploads/petrol_d_ecto_new.png"></td>
            <td>1.617 EUR</td><td>ADUS Ulmaņa: Kārļa Ulmaņa gatve 67, Rīga.</td></tr></table>
        """)
        self.assertEqual(
            [(row.fuel_code, row.price_eur_l, row.dus_address) for row in rows],
            [("Ecto-DD", 1.617, "ADUS Ulmaņa: Kārļa Ulmaņa gatve 67, Rīga")],
        )

    def api_price_html(self) -> str:
        station = [("ADUS Ulmaņa", "Kārļa Ulmaņa gatve 67, Rīga")]
        return '<div class="fuel-table">' + "".join([
            fuel_row("95 Multi FX", "1.607", station),
            fuel_row("95 Multi FX plus", "1.632", station),
            fuel_row("98 Multi FX", "1.712", station),
            fuel_row("D", "1.914", [("DUS Dārzciema", "Dārzciema iela 69, Rīga")]),
            fuel_row("D Multi FX", "1.807", station),
            fuel_row("Gāze", "1.117", station),
            fuel_row("E85", "1.995", station),
        ]) + "</div>"

    def test_valid_price_page_does_not_request_the_api(self) -> None:
        with requests.Session() as session, patch(
            FETCH_HTML, return_value=self.api_price_html()
        ) as fetch:
            rows = list(ViadaScraper(session).scrape("2026-11-27T08:40+02:00"))
            fetch.assert_called_once_with(ViadaScraper.source_url, session=session)
        self.assertTrue(all(row.source_url == ViadaScraper.source_url for row in rows))

    def test_verification_page_uses_live_api_content_without_mixing_fuel_types(self) -> None:
        with requests.Session() as session, patch(
            FETCH_HTML, side_effect=[CHALLENGE_HTML, api_response(self.api_price_html())]
        ) as fetch:
            with self.assertLogs(level="WARNING") as logs:
                rows = list(ViadaScraper(session).scrape("2026-11-27T08:40+02:00"))
            self.assertEqual(
                [call.args[0] for call in fetch.call_args_list],
                [ViadaScraper.source_url, ViadaScraper.api_url],
            )
        self.assertIn("One moment, please...", " ".join(logs.output))
        self.assertEqual(
            [(row.fuel_code, row.fuel_name_raw, row.price_eur_l) for row in rows],
            [
                ("Ecto-95", "95 Multi FX", 1.607),
                ("Ecto-95+", "95 Multi FX plus", 1.632),
                ("E98", "98 Multi FX", 1.712),
                ("DD", "D", 1.914),
                ("Ecto-DD", "D Multi FX", 1.807),
                ("LPG", "Gāze", 1.117),
                ("E85", "E85", 1.995),
            ],
        )
        self.assertTrue(all(row.source_url == ViadaScraper.api_url for row in rows))
        self.assertEqual(rows[3].dus_address, "DUS Dārzciema : Dārzciema iela 69, Rīga")

    def test_http_error_also_uses_the_api(self) -> None:
        with requests.Session() as session, patch(
            FETCH_HTML,
            side_effect=[requests.HTTPError("403 Forbidden"), api_response(self.api_price_html())],
        ):
            rows = list(ViadaScraper(session).scrape("2026-11-27T08:40+02:00"))
        self.assertEqual(len(rows), 7)

    def test_api_for_another_page_is_rejected(self) -> None:
        with requests.Session() as session, patch(
            FETCH_HTML,
            side_effect=[CHALLENGE_HTML, api_response(self.api_price_html(), link="https://www.viada.lv/")],
        ):
            with self.assertRaisesRegex(ScrapeError, "did not return the official Latvian price page"):
                list(ViadaScraper(session).scrape("2026-11-27T08:40+02:00"))

    def test_incomplete_api_content_is_rejected(self) -> None:
        for response in [
            CHALLENGE_HTML,
            api_response("<p>No prices</p>"),
            api_response(fuel_row("95 Multi FX", "1.607", [])),
            api_response("", content=None),
        ]:
            with self.subTest(response=response[:70]), requests.Session() as session, patch(
                FETCH_HTML, side_effect=[CHALLENGE_HTML, response]
            ):
                with self.assertRaisesRegex(ScrapeError, "official page API failed"):
                    list(ViadaScraper(session).scrape("2026-11-27T08:40+02:00"))
