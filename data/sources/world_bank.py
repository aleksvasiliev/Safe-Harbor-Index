"""
World Bank Open Data API fetcher.
Free, no API key required.
Docs: https://datahelpdesk.worldbank.org/knowledgebase/articles/898581
"""

import requests
import json
import time

# World Bank indicator codes
INDICATORS = {
    "stability":  "PV.EST",           # Political Stability & Absence of Violence (-2.5..+2.5)
    "rule_of_law": "RL.EST",          # Rule of Law (-2.5..+2.5)
    "corruption":  "CC.EST",          # Control of Corruption (-2.5..+2.5)
    "gdp_pc":      "NY.GDP.PCAP.CD",  # GDP per capita (current USD)
    "unemployment":"SL.UEM.TOTL.ZS",  # Unemployment, total (% of labor force)
    "pop_density": "EN.POP.DNST",     # Population density (people per km²)
    "food_idx":    "AG.PRD.FOOD.XD",  # Food Production Index (2014-2016=100)
    "life_exp":    "SP.DYN.LE00.IN",  # Life expectancy at birth (years)
    "internet":    "IT.NET.USER.ZS",  # Individuals using the Internet (% of population)
    "health_exp":  "SH.XPD.CHEX.GD.ZS", # Current health expenditure (% of GDP)
    "homicide":    "VC.IHR.PSRC.P5",  # Intentional homicides (per 100,000 people)
    "military_exp":"MS.MIL.XPND.GD.ZS", # Military expenditure (% of GDP)
}

# ISO numeric → World Bank alpha-3
COUNTRY_CODES = {
    "840": "USA", "124": "CAN", "036": "AUS", "554": "NZL", "356": "IND",
    "156": "CHN", "643": "RUS", "076": "BRA", "276": "DEU", "250": "FRA",
    "826": "GBR", "380": "ITA", "724": "ESP", "620": "PRT", "528": "NLD",
    "752": "SWE", "578": "NOR", "208": "DNK", "246": "FIN", "756": "CHE",
    "040": "AUT", "203": "CZE", "703": "SVK", "705": "SVN", "191": "HRV",
    "348": "HUN", "616": "POL", "642": "ROU", "100": "BGR", "300": "GRC",
    "233": "EST", "428": "LVA", "440": "LTU", "372": "IRL", "442": "LUX",
    "352": "ISL", "792": "TUR", "804": "UKR", "112": "BLR", "498": "MDA",
    "688": "SRB", "376": "ISR", "364": "IRN", "784": "ARE", "682": "SAU",
    "400": "JOR", "422": "LBN", "818": "EGY", "504": "MAR", "788": "TUN",
    "012": "DZA", "710": "ZAF", "404": "KEN", "410": "KOR", "392": "JPN",
    "702": "SGP", "458": "MYS", "764": "THA", "704": "VNM", "360": "IDN",
    "608": "PHL", "398": "KAZ", "496": "MNG", "268": "GEO", "051": "ARM",
    "586": "PAK", "050": "BGD", "484": "MEX", "170": "COL", "604": "PER",
    "032": "ARG", "152": "CHL", "858": "URY", "068": "BOL", "218": "ECU",
    "600": "PRY", "188": "CRI", "591": "PAN", "192": "CUB", "214": "DOM",
    "566": "NGA", "231": "ETH",
}

WB_ALPHA3_TO_NUMERIC = {v: k for k, v in COUNTRY_CODES.items()}
BASE_URL = "https://api.worldbank.org/v2"


def fetch_indicator(indicator_code: str, year_range: str = "2018:2023") -> dict:
    """Fetch indicator for all our countries. Returns {wb_code: value}."""
    codes = ";".join(COUNTRY_CODES.values())
    url = (
        f"{BASE_URL}/country/{codes}/indicator/{indicator_code}"
        f"?format=json&mrv=5&per_page=500&date={year_range}"
    )
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  ERROR fetching {indicator_code}: {e}")
        return {}

    results = {}
    if len(data) < 2 or not data[1]:
        return results

    for entry in data[1]:
        if entry.get("value") is not None:
            iso3 = entry["countryiso3code"]
            numeric = WB_ALPHA3_TO_NUMERIC.get(iso3)
            if numeric and numeric not in results:  # take most recent
                results[numeric] = entry["value"]

    return results


def fetch_all(cache_path: str = None) -> dict:
    """Fetch all indicators. Returns {numeric_id: {indicator: value}}."""
    all_data = {num: {} for num in COUNTRY_CODES}

    for name, code in INDICATORS.items():
        print(f"  Fetching {name} ({code})...")
        values = fetch_indicator(code)
        for numeric, val in values.items():
            all_data[numeric][name] = val
        time.sleep(0.5)  # be polite to the API

    if cache_path:
        with open(cache_path, "w") as f:
            json.dump(all_data, f, indent=2)
        print(f"  Cached to {cache_path}")

    return all_data
