# TECHi scrape + traffic analysis

Two deliverables: a scraper that builds `techi_articles.csv` from six TECHi
category pages, and an analysis script that answers four questions against
that file plus `traffic_table.csv`.

## Setup

```
python3 -m pip install requests beautifulsoup4 pandas matplotlib
```

Python 3.9+ is assumed. Matplotlib runs headless (`Agg`), so no display is
needed.

## Run

```
python3 scrape_techi.py      # writes techi_articles.csv (120 rows), ~10s (2s sleep between requests)
python3 analyze_traffic.py   # prints all four analyses, writes chart1_sessions_break.png, chart2_feb_jump.png
```

Run the scraper first: the analysis reads its output.

## Files

- `scrape_techi.py` - the scraper.
- `method.txt` - field definitions, exact derived rules, limitations.
- `techi_articles.csv` - real scraped output (120 rows, 9 columns, no blanks).
- `analyze_traffic.py` - pandas/matplotlib analysis.
- `memo.md` - the business answers.
- `chart1_sessions_break.png`, `chart2_feb_jump.png` - 300 dpi, greyscale-safe.

## Data separation (important)

`techi_articles.csv` is real, scraped data. `traffic_table.csv` is the supplied
12-month dataset and is treated as a given input. The two are never merged
row-by-row; they share only section names.

## Key analytical decisions and tradeoffs

- Six requests, not 126. The category listings already server-render URL,
  headline, author and date, so no article page is fetched. Fewer requests and
  less load; the tradeoff is card-level fields only (no body text or views).
- Canonical slugs. The friendly `/category/ai/` URLs 404 or redirect, so the
  six canonical slugs are hard-coded.
- `Accept-Encoding: gzip, deflate` is pinned because the site's default zstd
  responses crash this urllib3 build.
- Derived fields are rule-based (regex), not models, so they are reproducible
  and documentable. Tradeoff: a hard-coded ~85-name company list misses firms
  that are not on it.
- True same-month YoY is reported as **not computable** (0 prior-year pairs in
  a 12-month file) rather than invented. Two clearly labelled proxies are used
  instead: half-over-half means and endpoints.
- The tracking-inflation multiplier is derived from the data itself:
  `A = M / (1+g) = 1.4795 / 1.0271 = 1.4404`, where `M` is the Jan->Feb total
  jump and `1+g` is the de-spiked pre-swap geometric-mean monthly growth.
  Tradeoff: `A` is one uniform multiplier for all sections because the boundary
  jump was uniform. It therefore also deepens genuine declines (Guides).

## Data validation checks run

- Row and section counts: 120 rows, 20 per section, 6 sections.
- No blank values anywhere (the scraper aborts instead of saving if any exist).
- `date_shown` split into 91 parseable absolute dates and 29 relative labels.
- Traffic file read as 12 monthly rows, 2025-09..2026-08.
- Post-swap boundary checked for uniformity across all six sections (41-49%).
- Charts verified at 300 dpi with greyscale-safe encodings (line style, marker,
  and hatch instead of colour alone).

## What I would improve with more time

- Fetch more than 20 articles per section (pagination) and absolute dates for
  every card, so period claims such as the Sep-2025 hire become testable.
- Add a category-overlap check: an article can appear in more than one section.
- Replace the hard-coded company list with a versioned, reviewable reference
  file, and add unit tests for the regex rules.
- Pull Google Search Console (free) as an independent session counter to test
  whether the 1 Feb 2026 jump is real or an artefact.
- Model the adjustment per section instead of one uniform multiplier `A`.
