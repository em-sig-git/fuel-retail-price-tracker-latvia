# Baltic Fuel Price Scraper

GitHub Actions fuel price scraper for Latvian fuel retailers, designed so country-level scrapers can be added later for Lithuania and Estonia.

## Current coverage

- Latvia / Circle K
- Latvia / Neste
- Latvia / Virši
- Latvia / Viada
- Latvia / KOOL
- Latvia / Latvijas Nafta

## Output

The scraper maintains a long-format CSV at:

- `data/fuel_prices_latvia.csv`

Columns:

- `timestamp`
- `country`
- `brand`
- `fuel_code`
- `fuel_name_raw`
- `price_eur_l`
- `dus_address`
- `source_url`
- `note`
- `scraped_at`

Deduplication key:

- `timestamp`
- `country`
- `brand`
- `fuel_code`
- `dus_address`

## GitHub Actions

Workflow file:

- `.github/workflows/scrape_fuel_prices.yml`

Default schedule runs every 3 hours and supports manual runs.

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.baltic_fuel_price_scraper.main
```
