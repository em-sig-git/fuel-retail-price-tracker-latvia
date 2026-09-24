from __future__ import annotations
 
from typing import Iterable, List
 
from bs4 import BeautifulSoup
 
from ..models import FuelRecord
from ..utils import clean_text, extract_first_decimal, fetch_html, normalize_address, soupify
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
 
 
class VirsiScraper(BaseBrandScraper):
    brand = "Virši"
    source_url = "https://www.virsi.lv/lv/privatpersonam/degviela/degvielas-un-elektrouzlades-cenas"
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
    VirsiScraper,
    ViadaScraper,
    LatvijasNaftaScraper,
]
