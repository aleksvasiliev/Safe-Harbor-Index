"""
Numbeo HTML scraper — country-level indices.
Scrapes public ranking pages (no API key needed).

Provides:
  - Crime Index        → safety (inverted)
  - Safety Index       → safety
  - Health Care Index  → health
  - Cost of Living Index → cost (inverted)
"""

import json
import re
import time

import requests
from bs4 import BeautifulSoup

URLS = {
    "cost":     "https://www.numbeo.com/cost-of-living/rankings_by_country.jsp",
    "crime":    "https://www.numbeo.com/crime/rankings_by_country.jsp",
    "health":   "https://www.numbeo.com/health-care/rankings_by_country.jsp",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Numbeo country name → ISO numeric code
NUMBEO_NAME_TO_NUMERIC = {
    "United States": "840", "Canada": "124", "Australia": "036",
    "New Zealand": "554", "India": "356", "China": "156",
    "Russia": "643", "Brazil": "076", "Germany": "276",
    "France": "250", "United Kingdom": "826", "Italy": "380",
    "Spain": "724", "Portugal": "620", "Netherlands": "528",
    "Sweden": "752", "Norway": "578", "Denmark": "208",
    "Finland": "246", "Switzerland": "756", "Austria": "040",
    "Czech Republic": "203", "Slovakia": "703", "Slovenia": "705",
    "Croatia": "191", "Hungary": "348", "Poland": "616",
    "Romania": "642", "Bulgaria": "100", "Greece": "300",
    "Estonia": "233", "Latvia": "428", "Lithuania": "440",
    "Ireland": "372", "Luxembourg": "442", "Iceland": "352",
    "Turkey": "792", "Ukraine": "804", "Belarus": "112",
    "Moldova": "498", "Serbia": "688", "Israel": "376",
    "Iran": "364", "United Arab Emirates": "784", "Saudi Arabia": "682",
    "Jordan": "400", "Lebanon": "422", "Egypt": "818",
    "Morocco": "504", "Tunisia": "788", "Algeria": "012",
    "South Africa": "710", "Kenya": "404", "South Korea": "410",
    "Japan": "392", "Singapore": "702", "Malaysia": "458",
    "Thailand": "764", "Vietnam": "704", "Indonesia": "360",
    "Philippines": "608", "Kazakhstan": "398", "Mongolia": "496",
    "Georgia": "268", "Armenia": "051", "Pakistan": "586",
    "Bangladesh": "050", "Mexico": "484", "Colombia": "170",
    "Peru": "604", "Argentina": "032", "Chile": "152",
    "Uruguay": "858", "Bolivia": "068", "Ecuador": "218",
    "Paraguay": "600", "Costa Rica": "188", "Panama": "591",
    "Cuba": "192", "Dominican Republic": "214", "Nigeria": "566",
    "Ethiopia": "231",
}


def _get(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def _parse_float(text: str):
    text = text.strip().replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _scrape_cost(soup: BeautifulSoup) -> dict:
    """Returns {country_name: cost_of_living_index}"""
    result = {}
    table = soup.find("table", class_="stripe")
    if not table:
        print("  WARNING: cost-of-living table not found")
        return result
    for row in table.find("tbody").find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue
        name = cells[1].get_text(strip=True)
        val = _parse_float(cells[2].get_text())
        if val is not None:
            result[name] = val
    return result


def _scrape_crime(soup: BeautifulSoup) -> dict:
    """Returns {country_name: {crime_index, safety_index}}"""
    result = {}
    table = soup.find("table", class_="stripe")
    if not table:
        print("  WARNING: crime table not found")
        return result
    for row in table.find("tbody").find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue
        name = cells[1].get_text(strip=True)
        crime = _parse_float(cells[2].get_text())
        safety = _parse_float(cells[3].get_text())
        if crime is not None:
            result[name] = {"crime_index": crime, "safety_index": safety}
    return result


def _scrape_health(soup: BeautifulSoup) -> dict:
    """Returns {country_name: health_care_index}"""
    result = {}
    # Healthcare page uses a DataTable — try table.stripe first, then any table
    table = soup.find("table", class_="stripe")
    if not table:
        # Fallback: look for table with id containing 'tblMain'
        table = soup.find("table", id=re.compile(r"tbl", re.I))
    if not table:
        print("  WARNING: healthcare table not found")
        return result
    tbody = table.find("tbody")
    if not tbody:
        return result
    for row in tbody.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue
        name = cells[1].get_text(strip=True)
        val = _parse_float(cells[2].get_text())
        if val is not None:
            result[name] = val
    return result


def fetch_country_indices(api_key: str = None, cache_path: str = None) -> dict:
    """
    Scrape Numbeo public ranking pages.
    api_key is ignored (kept for API compatibility with update.py).
    Returns {numeric_id: {crime_index, safety_index, health_care_index, cost_of_living_index}}
    """
    print("  Scraping Numbeo cost-of-living...")
    cost_data = _scrape_cost(_get(URLS["cost"]))
    time.sleep(1)

    print("  Scraping Numbeo crime/safety...")
    crime_data = _scrape_crime(_get(URLS["crime"]))
    time.sleep(1)

    print("  Scraping Numbeo healthcare...")
    health_data = _scrape_health(_get(URLS["health"]))

    print(f"  Got: {len(cost_data)} cost, {len(crime_data)} crime, {len(health_data)} health entries")

    results = {}
    all_names = set(cost_data) | set(crime_data) | set(health_data)
    for name in all_names:
        numeric = NUMBEO_NAME_TO_NUMERIC.get(name)
        if not numeric:
            continue
        entry = {}
        if name in cost_data:
            entry["cost_of_living_index"] = cost_data[name]
        if name in crime_data:
            entry["crime_index"] = crime_data[name]["crime_index"]
            entry["safety_index"] = crime_data[name]["safety_index"]
        if name in health_data:
            entry["health_care_index"] = health_data[name]
        results[numeric] = entry

    if cache_path:
        with open(cache_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"  Cached to {cache_path}")

    return results
