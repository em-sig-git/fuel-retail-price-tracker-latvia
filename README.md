# Latvia fuel retail price tracker

Collects published fuel prices from Latvian retailer websites and stores the
validated observations in `data/fuel_prices_latvia.csv`.

## Active sources

- Circle K
- Virši
- Viada
- Latvijas Nafta

Neste and KOOL are intentionally excluded from new collection:

- Neste stopped publishing a price table and now directs customers to station
  price pylons and pumps. Historical Neste rows are retained through
  `2026-08-10T08:47+03:00`.
- KOOL publishes prices as independent, absolutely positioned presentation
  widgets rather than a stable table or structured feed. A layout change first
  corrupted the dataset at `2026-04-23T06:10+03:00`. KOOL observations through
  `2026-04-22T08:34+03:00` are retained; later observations are removed.

## Data-quality policy

Each source is validated independently before its observations are accepted. A
source contributes no rows when it fails validation, while valid observations
from other sources are still saved. The entire run fails only when no source
produces valid rows.

For an individual source, validation requires that it:

- returns at least one row and all required core fuel types;
- returns prices between 0.50 and 3.00 EUR/L;
- returns a non-empty address that does not contain known promotional text;
- uses an HTTPS source URL; and
- contains no duplicate fuel/address pair.

Limits are conservative guards against parser failures; update them deliberately
if the market moves outside them.

## Installation and execution

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m src.fuel_retail_price_tracker_latvia.main
```
