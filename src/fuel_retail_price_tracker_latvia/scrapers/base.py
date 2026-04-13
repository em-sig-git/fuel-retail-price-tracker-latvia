from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

import requests

from ..models import FuelRecord


class BaseBrandScraper(ABC):
    brand: str
    country: str = "LV"
    source_url: str

    def __init__(self, session: requests.Session) -> None:
        self.session = session

    @abstractmethod
    def scrape(self, timestamp: str) -> Iterable[FuelRecord]:
        raise NotImplementedError
