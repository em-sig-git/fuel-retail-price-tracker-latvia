from __future__ import annotations
 
import logging
import re
from collections import defaultdict
from typing import Iterable, List
 
from bs4 import BeautifulSoup
 
from ..models import FuelRecord
from ..utils import (
    clean_multiline_text,
    clean_text,
    extract_first_decimal,
    fetch_html,
    normalize_address,
    soupify,
)
from .base import BaseBrandScraper
 
 
class CircleKScraper(BaseBrandScraper):
    brand = "Circle K"
    source_url = "https://www.circlek.lv/degviela-miles/degvielas-cenas"
    fuel_map = {
        "95miles": "E95",
        "98miles+": "E98",
        "Dmiles": "DD",
        "Dmiles+": "DD+",
        "Autogāze": "LPG",
    }
 
    def scrape(self, timestamp: str) -> Iterable[FuelRecord]:
        html = fetch_html(self.source_url, session=self.session)
        soup = soupify(html)
        records: List[FuelRecord] = []
        for row in soup.select("table tr"):
            cells = [clean_text(cell.get_text(" ", strip=True)) for cell in row.select("th, td")]
            if len(cells) < 3:
                continue
            raw_name = cells[0]
            fuel_code = self.fuel_map.get(raw_name)
            if not fuel_code:
                continue
            price = extract_first_decimal(cells[1])
            if price is None:
                continue
            address = normalize_address(cells[2])
            records.append(
                FuelRecord(
                    timestamp=timestamp,
                    country=self.country,
                    brand=self.brand,
                    fuel_code=fuel_code,
                    fuel_name_raw=raw_name,
                    price_eur_l=price,
                    dus_address=address,
                    source_url=self.source_url,
                    note="",
                )
            )
        return records
 
 
class NesteScraper(BaseBrandScraper):
    brand = "Neste"
    source_url = "https://www.neste.lv/lv/content/degvielas-cenas"
    fuel_map = {
        "Neste Futura 95": "E95",
        "Neste Futura 98": "E98",
        "Neste Futura D": "DD",
        "Neste Pro Diesel": "DD+",
    }
 
    def scrape(self, timestamp: str) -> Iterable[FuelRecord]:
        html = fetch_html(self.source_url, session=self.session)
        soup = soupify(html)
        records: List[FuelRecord] = []
        for row in soup.select("table tr"):
            cells = [clean_text(cell.get_text(" ", strip=True)) for cell in row.select("td, th")]
            if len(cells) < 3:
                continue
            raw_name = cells[0]
            fuel_code = self.fuel_map.get(raw_name)
            if not fuel_code:
                continue
            price = extract_first_decimal(cells[1])
            if price is None:
                continue
            records.append(
                FuelRecord(
                    timestamp=timestamp,
                    country=self.country,
                    brand=self.brand,
                    fuel_code=fuel_code,
                    fuel_name_raw=raw_name,
                    price_eur_l=price,
                    dus_address=normalize_address(cells[2]),
                    source_url=self.source_url,
                    note="",
                )
            )
        return records
 
 
class VirsiScraper(BaseBrandScraper):
    brand = "Virši"
    source_url = "https://www.virsi.lv/lv/privatpersonam/elektriba/degvielas-cena"
    fuel_map = {
        "95E": "E95",
        "98E": "E98",
        "DD": "DD",
        "CNG": "CNG",
        "LPG": "LPG",
    }
 
    def scrape(self, timestamp: str) -> Iterable[FuelRecord]:
        html = fetch_html(self.source_url, session=self.session)
        soup = soupify(html)
        records: List[FuelRecord] = []
        for card in soup.select(".price-card"):
            spans = card.select("p.price span")
            if len(spans) < 2:
                continue
            raw_name = clean_text(spans[0].get_text())
            fuel_code = self.fuel_map.get(raw_name)
            if not fuel_code:
                continue
            price = extract_first_decimal(spans[1].get_text())
            if price is None:
                continue
            address_node = card.select_one("p.address")
            address = normalize_address(address_node.get_text(" ", strip=True)) if address_node else ""
            records.append(
                FuelRecord(
                    timestamp=timestamp,
                    country=self.country,
                    brand=self.brand,
                    fuel_code=fuel_code,
                    fuel_name_raw=raw_name,
                    price_eur_l=price,
                    dus_address=address,
                    source_url=self.source_url,
                    note="",
                )
            )
        return records
 
 
class ViadaScraper(BaseBrandScraper):
    brand = "Viada"
    source_url = "https://www.viada.lv/zemakas-degvielas-cenas/"
    fuel_map = {
        "petrol_95ecto_new.png": "Ecto-95",
        "petrol_95ectoplus_new.png": "Ecto-95+",
        "petrol_98_new.png": "E98",
        "petrol_d_new.png": "DD",
        "petrol_d_ecto_new.png": "Ecto-DD",
        "petrol_e85_new.png": "E85",
        "GAZE.png": "LPG",
    }
 
    def __init__(self, session: requests.Session) -> None:
        import requests as _req
        viada_session = _req.Session()
        viada_session.verify = False
        super().__init__(viada_session)
 
 
    def scrape(self, timestamp: str) -> Iterable[FuelRecord]:
        html = fetch_html(self.source_url, session=self.session)
        soup = soupify(html)
        records: List[FuelRecord] = []
        for row in soup.select("table tr"):
            cells = row.select("td")
            if len(cells) < 3:
                continue
            img = cells[0].select_one("img")
            if not img:
                continue
            src = img.get("src", "")
            key = src.rsplit("/", 1)[-1]
            fuel_code = self.fuel_map.get(key)
            if not fuel_code:
                continue
            price = extract_first_decimal(cells[1].get_text(" ", strip=True))
            if price is None:
                continue
            raw_name = fuel_code
            address = normalize_address(clean_text(cells[2].get_text(" ", strip=True)))
            records.append(
                FuelRecord(
                    timestamp=timestamp,
                    country=self.country,
                    brand=self.brand,
                    fuel_code=fuel_code,
                    fuel_name_raw=raw_name,
                    price_eur_l=price,
                    dus_address=address,
                    source_url=self.source_url,
                    note="Multiple DUS may share one price row",
                )
            )
        return records
 
 
class KoolScraper(BaseBrandScraper):
    brand = "KOOL"
    source_url = "https://www.kool.lv/degviela/"
    fuel_map = {
        "95E": "E95",
        "98*": "E98",
        "DD": "DD",
        "kool premium diesel**": "DD+",
    }
 
    @staticmethod
    def _extract_top_left(style: str) -> tuple[float, float]:
        top_match = re.search(r"top:\s*([\d.]+)px", style or "")
        left_match = re.search(r"left:\s*([\d.]+)px", style or "")
        top = float(top_match.group(1)) if top_match else -1.0
        left = float(left_match.group(1)) if left_match else -1.0
        return top, left
 
    def _fetch_rendered_html(self) -> str:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox", "--disable-setuid-sandbox"])
            page = browser.new_page()
            page.goto(self.source_url, wait_until="domcontentloaded", timeout=60000)
            # state="attached" avoids the fonts-pending visibility deadlock
            page.wait_for_selector("div.rmwidget.widget-text-v3", state="attached", timeout=30000)
            # Let the page builder finish populating widgets, but don't hard-fail
            # if the page never reaches networkidle (e.g. analytics pings)
            try:
                page.wait_for_load_state("networkidle", timeout=20000)
            except PlaywrightTimeout:
                logging.warning("KOOL: networkidle timeout, proceeding with partial DOM")
            html = page.content()
            browser.close()
        return html
 
    def scrape(self, timestamp: str) -> Iterable[FuelRecord]:
        html = self._fetch_rendered_html()
        soup = soupify(html)
        widget_count = len(soup.select("div.rmwidget.widget-text-v3"))
        logging.info("KOOL: found %d widget-text-v3 elements in fetched HTML", widget_count)
 
        text_widgets = []
        for widget in soup.select("div.rmwidget.widget-text-v3"):
            text = clean_multiline_text(widget.get_text("\n", strip=True))
            if not text:
                continue
            top, left = self._extract_top_left(widget.get("style", ""))
            text_widgets.append({"text": text, "top": top, "left": left})
 
        def _dash_line_count(w: dict) -> int:
            return sum(1 for line in w["text"].splitlines() if clean_text(line).startswith("-"))

        address_block = max(text_widgets, key=_dash_line_count, default=None)
        if not address_block or _dash_line_count(address_block) < 2:
            logging.warning("KOOL: could not identify address block (no widget with >=2 dash-prefixed lines)")
            return []
 
        address_lines = []
        for line in address_block["text"].splitlines():
            line = clean_text(line)
            if line.startswith("-"):
                address_lines.append(normalize_address(line.lstrip("-")))
 
        if not address_lines:
            return []
 
        row_groups = defaultdict(list)
        for widget in text_widgets:
            text = widget["text"]
            if widget["top"] < 150 or widget["top"] > 420:
                continue
            if widget is address_block:
                continue
            if re.search(r"\d+[.,]\d+", text) or text.lower() in {k.lower() for k in self.fuel_map}:
                row_id = 0 if widget["top"] < 280 else 1
                row_groups[row_id].append(widget)
 
        records: List[FuelRecord] = []
        fuel_map_lower = {k.lower(): v for k, v in self.fuel_map.items()}
 
        for row_id, row_address in enumerate(address_lines):
            widgets = row_groups.get(row_id, [])
            labels = [w for w in widgets if w["text"].lower() in fuel_map_lower]
            prices = [w for w in widgets if re.search(r"\d+[.,]\d+", w["text"])]
            if not labels or not prices:
                continue
            prices_sorted = sorted(prices, key=lambda x: x["left"])
            for label in labels:
                nearest_price = min(prices_sorted, key=lambda x: abs(x["left"] - label["left"]))
                price = extract_first_decimal(nearest_price["text"])
                if price is None:
                    continue
                raw_name = label["text"]
                records.append(
                    FuelRecord(
                        timestamp=timestamp,
                        country=self.country,
                        brand=self.brand,
                        fuel_code=fuel_map_lower[raw_name.lower()],
                        fuel_name_raw=raw_name,
                        price_eur_l=price,
                        dus_address=row_address,
                        source_url=self.source_url,
                        note="Parsed from positioned page widgets",
                    )
                )
        return records
 
 
class LatvijasNaftaScraper(BaseBrandScraper):
    brand = "Latvijas Nafta"
    source_url = "https://www.lnafta.lv/lv/start/dus-tikls"
    fuel_map = {
        "95 E": "E95",
        "98 E": "E98",
        "DD Eiro": "DD",
        "DDL**": "DD+",
        "Auto gāze": "LPG",
    }
 
    def scrape(self, timestamp: str) -> Iterable[FuelRecord]:
        html = fetch_html(self.source_url, session=self.session)
        soup = soupify(html)
        records: List[FuelRecord] = []
 
        for table in soup.select("table.dusRegion"):
            header_cells = [clean_text(th.get_text(" ", strip=True)) for th in table.select("tr:first-child th")]
            if not header_cells:
                continue
            fuel_indexes = {
                idx: self.fuel_map[header]
                for idx, header in enumerate(header_cells)
                if header in self.fuel_map
            }
            if not fuel_indexes:
                continue
 
            rows = table.select("tr")[1:]
            for row in rows:
                cells = row.select("td")
                if len(cells) < len(header_cells):
                    continue
                address = normalize_address(clean_text(cells[0].get_text(" ", strip=True)))
                for idx, fuel_code in fuel_indexes.items():
                    raw_value = clean_text(cells[idx].get_text(" ", strip=True))
                    price = extract_first_decimal(raw_value)
                    if price is None:
                        continue
                    raw_name = header_cells[idx]
                    records.append(
                        FuelRecord(
                            timestamp=timestamp,
                            country=self.country,
                            brand=self.brand,
                            fuel_code=fuel_code,
                            fuel_name_raw=raw_name,
                            price_eur_l=price,
                            dus_address=address,
                            source_url=self.source_url,
                            note="Only rows with numeric values are recorded",
                        )
                    )
        return records
 
 
LATVIA_SCRAPERS = [
    CircleKScraper,
    NesteScraper,
    VirsiScraper,
    ViadaScraper,
    KoolScraper,
    LatvijasNaftaScraper,
]
