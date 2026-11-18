#!/usr/bin/env python3
"""Scrape the 20 newest articles from six TECHi category pages.

Outputs ``techi_articles.csv`` (120 rows, 9 columns, no blank values) and
prints a per-section summary before saving.

Design notes
------------
* Only six HTTP requests are made -- one per category listing page. The
  listing markup already carries the URL, headline, author and the shown
  date, so no article page needs to be fetched.
* A 2 second pause is enforced between every pair of requests.
* ``format``, ``names_a_company`` and ``contains_a_number`` are derived
  purely from the headline text using fixed, rule-based logic (no external
  APIs, no models). The exact rules are documented in method.txt.
"""

import csv
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# --- Configuration ---------------------------------------------------------

BASE_URL = "https://www.techi.com"

# Requested section label -> canonical category slug on the live site.
# The friendly URLs (/category/ai/, /category/markets/, ...) either redirect
# or 404; these are the canonical slugs the site's own navigation links to.
CATEGORIES = [
    ("ai", "ai-intelligence"),
    ("markets", "markets-equities"),
    ("crypto", "crypto-defi"),
    ("breakthroughs", "tech-breakthroughs"),
    ("policy", "policy-impact"),
    ("guides", "research-tools-guides"),
]

ARTICLES_PER_SECTION = 20
SLEEP_SECONDS = 2          # pause required between every HTTP request
REQUEST_TIMEOUT = 30
CSV_PATH = "techi_articles.csv"

# Column order of the output file.
COLUMNS = [
    "url",
    "section",
    "headline",
    "author",
    "date_shown",
    "headline_word_count",
    "format",
    "names_a_company",
    "contains_a_number",
]

# Fixed list of company/organisation names (and common aliases) used by the
# deterministic ``names_a_company`` rule below. Matched case-insensitively.
COMPANIES = [
    "nvidia", "amd", "intel", "microsoft", "openai", "anthropic", "google",
    "alphabet", "amazon", "aws", "apple", "meta", "facebook", "tesla",
    "spacex", "xai", "starlink", "ibm", "oracle", "qualcomm", "tsmc",
    "samsung", "micron", "broadcom", "arm holdings", "cisco", "adobe",
    "salesforce", "netflix", "paypal", "uber", "airbnb", "coinbase",
    "binance", "kraken", "circle", "tether", "ripple", "solana",
    "ethereum", "bitcoin", "palantir", "snowflake", "databricks",
    "hugging face", "mistral", "cohere", "cerebras", "groq", "ionq",
    "coreweave", "oklo", "centrus", "blackstone", "visa", "mastercard",
    "jpmorgan", "goldman sachs", "morgan stanley", "blackrock", "nasdaq",
    "msci", "boeing", "lockheed martin", "rivian", "lucid", "ford",
    "toyota", "honda", "sony", "nintendo", "spotify", "tiktok",
    "bytedance", "alibaba", "tencent", "baidu", "huawei", "xiaomi",
    "deepseek", "z.ai", "softbank", "advantest", "tokyo electron",
    "sanmina", "rohm", "shibaura", "nrg", "fodere", "novatech", "einride",
    "black forest labs", "stargate",
]

# Pre-compile the company matcher: lowercase headline, match whole "words".
_COMPANY_PATTERN = re.compile(
    r"(?<![a-z0-9])(" + "|".join(re.escape(c) for c in COMPANIES) + r")(?![a-z0-9])"
)

# Headline-format rules (checked in order, first match wins).
_HOW_PATTERN = re.compile(r"(?i)^how\b")
_LIST_PATTERN = re.compile(
    r"(?i)^(top\s+\d+\b"
    r"|\d+\s+(?:best|ways|things|tips|tools|reasons|examples|steps|trends"
    r"|picks|alternatives|mistakes|lessons|platforms)\b"
    r"|best\b)"
)
_NUMBER_PATTERN = re.compile(r"\d")


# --- Derived-field rules ---------------------------------------------------

def headline_word_count(headline: str) -> int:
    """Number of whitespace-separated tokens in the headline."""
    return len(headline.split())


def classify_format(headline: str) -> str:
    """Rule-based headline format: question | how-to | list | standard."""
    if headline.rstrip().endswith("?"):
        return "question"
    if _HOW_PATTERN.match(headline):
        return "how-to"
    if _LIST_PATTERN.match(headline):
        return "list"
    return "standard"


def names_a_company(headline: str) -> bool:
    """True when the headline contains a name from the fixed company list."""
    return bool(_COMPANY_PATTERN.search(headline.lower()))


def contains_a_number(headline: str) -> bool:
    """True when the headline contains at least one digit (0-9)."""
    return bool(_NUMBER_PATTERN.search(headline))


# --- Scraping --------------------------------------------------------------

def build_session() -> requests.Session:
    """A session with a browser-like User-Agent.

    Accept-Encoding is pinned to gzip/deflate: some urllib3 builds cannot
    decode the site's default zstd responses.
    """
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            ),
            "Accept-Encoding": "gzip, deflate",
        }
    )
    return session


def parse_section(html: str, section: str):
    """Extract up to ARTICLES_PER_SECTION newest article cards from one page.

    Cards are rendered server-side in document order (newest first), so the
    first N ``<article>`` elements are the N newest stories.
    """
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("article.techi-article-card")[:ARTICLES_PER_SECTION]

    rows = []
    for card in cards:
        headline_el = card.find("h2")
        time_el = card.find("time")
        author_el = card.select_one('a[href^="/@"]')
        link_el = card.find("a", href=True)

        # Skip a card only if it cannot yield a non-blank row; such cards are
        # reported by the validator below.
        if not (headline_el and time_el and author_el and link_el):
            continue

        headline = headline_el.get_text(strip=True)
        rows.append(
            {
                "url": urljoin(BASE_URL, link_el["href"]),
                "section": section,
                "headline": headline,
                "author": author_el.get_text(strip=True),
                # Verbatim text as shown on the page ("6 hours ago", "Oct 22, 2026").
                "date_shown": time_el.get_text(strip=True),
                "headline_word_count": headline_word_count(headline),
                "format": classify_format(headline),
                "names_a_company": names_a_company(headline),
                "contains_a_number": contains_a_number(headline),
            }
        )
    return rows


def fetch_section(session: requests.Session, slug: str) -> str:
    """Fetch one category listing page and return its HTML."""
    url = f"{BASE_URL}/category/{slug}/"
    response = session.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.text


# --- Validation & output ---------------------------------------------------

def find_missing(rows):
    """Return a list of (row_index, column) pairs whose value is blank."""
    problems = []
    for i, row in enumerate(rows):
        for col in COLUMNS:
            value = row.get(col)
            if value is None or (isinstance(value, str) and not value.strip()):
                problems.append((i, col))
    return problems


def main() -> int:
    session = build_session()

    rows = []
    section_counts = []

    for index, (label, slug) in enumerate(CATEGORIES):
        if index:                       # enforce the pause between requests
            time.sleep(SLEEP_SECONDS)

        html = fetch_section(session, slug)
        section_rows = parse_section(html, label)
        rows.extend(section_rows)
        section_counts.append((label, slug, len(section_rows)))
        print(f"  fetched section '{label}' ({slug}): {len(section_rows)} articles")

    # --- Summary before saving ---
    print("\nSummary per section:")
    for label, slug, count in section_counts:
        flag = "" if count == ARTICLES_PER_SECTION else "  <-- fewer than expected"
        print(f"  {label:<13} {count:>3} rows{flag}")
    print(f"  {'TOTAL':<13} {len(rows):>3} rows")

    # --- Missing-field check before saving ---
    problems = find_missing(rows)
    if problems:
        print(f"\n!! MISSING FIELDS: {len(problems)} blank value(s) found")
        for i, col in problems[:20]:
            print(f"   row {i}: column '{col}' is blank")
        print("Aborting save so the CSV never contains blank values.")
        return 1

    # --- Save ---
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nNo missing fields. Wrote {len(rows)} rows to {CSV_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
