from __future__ import annotations

import unittest
from unittest.mock import patch

import requests

from src.fuel_retail_price_tracker_latvia.scrapers.latvia import ViadaScraper
from src.fuel_retail_price_tracker_latvia.utils import ScrapeError
from src.fuel_retail_price_tracker_latvia.validation import validate_brand_records


FETCH_HTML = "src.fuel_retail_price_tracker_latvia.scrapers.latvia.fetch_html"


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
