"""
Numbeo API fetcher — country-level indices.
Free API key: register at https://www.numbeo.com/common/register.jsp

Provides:
  - Crime Index        → safety (inverted)
  - Safety Index       → safety
  - Health Care Index  → health
  - Cost of Living Index → cost (inverted)
"""

import requests
import json

BASE_URL = "https://www.numbeo.com/api"

# Numbeo country name → our ISO numeric code
# (Numbeo uses country names, not ISO codes)
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


def fetch_country_indices(api_key: str, cache_path: str = None) -> dict:
    """
    Fetch country-level indices from Numbeo.
    Returns {numeric_id: {crime_index, safety_index, health_care_index, cost_of_living_index}}
    """
    url = f"{BASE_URL}/country_indices?api_key={api_key}"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  ERROR fetching Numbeo: {e}")
        return {}

    results = {}
    for entry in data.get("elements", []):
        country = entry.get("country")
        numeric = NUMBEO_NAME_TO_NUMERIC.get(country)
        if not numeric:
            continue
        results[numeric] = {
            "crime_index":         entry.get("crime_index"),
            "safety_index":        entry.get("safety_index"),
            "health_care_index":   entry.get("health_care_index"),
            "cost_of_living_index": entry.get("cost_of_living_index"),
        }

    if cache_path:
        with open(cache_path, "w") as f:
            json.dump(results, f, indent=2)
        print(f"  Cached to {cache_path}")

    return results
