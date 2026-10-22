# Virši browser fallback

Virši can accept the existing HTTP scraper on a local PC while challenging a
GitHub-hosted runner. This change keeps the existing HTTP request first, then
uses Playwright Chromium when Virši returns HTTP 403, 429 or 503, or when its HTML
contains no price cards. It adapts the browser rendering approach used by the
earlier KOOL scraper (commit `15f79b172dd6ac56b0048492ddf2e4c67b2d72ca`).

Chromium executes page JavaScript and waits for the actual fuel-price elements.
Only the existing price parser's output reaches validation and storage. The
fallback has a bounded wait; a remaining challenge cannot become a price record.

The Actions workflow installs Chromium and its OS dependencies. Local runs that
succeed with the HTTP client do not launch a browser. To install the fallback
locally when needed:

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
python -m unittest discover -s tests -v
python -m src.fuel_retail_price_tracker_latvia.main
```

Apply the included `virsi-browser-fix.patch` from a current repository checkout,
then commit and run the Actions workflow. The patch does not change the stored
CSV, the other retailers' scrapers, or the existing policy for partial runs.

Browser fallback behavior and price parsing are covered by automated tests.
Successful Virši collection on a GitHub-hosted runner still needs an actual
Actions run: local or simulated tests cannot prove that Cloudflare accepts the
runner's network. This is a collection-path change, not a claim that the runner
has already passed verification.
