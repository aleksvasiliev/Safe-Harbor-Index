#!/usr/bin/env python3
"""
Safe Harbor Index — Data Update Pipeline
=========================================
Usage:
    python update.py                    # use cached data if fresh (<7 days)
    python update.py --refresh          # force re-fetch from APIs
    python update.py --numbeo-key KEY   # also fetch Numbeo data

What it does:
1. Fetches World Bank indicators (free, no key)
2. Optionally fetches Numbeo country indices (free API key needed)
3. Merges with manual_data.json (nuclear, geography, neighbors, etc.)
4. Normalizes everything to 1-10 scale
5. Injects updated COUNTRIES block into ../index.html

Data sources:
  - World Bank Open Data API  → stability, economy, employment, density,
                                food, health, tech, military (proxy)
  - Numbeo Country Indices    → cost, safety, health (quality)
  - manual_data.json          → nuclear, geography, neighbors, immigration,
                                resource, climate, crypto, taxes, business
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent))

from sources.world_bank import fetch_all as fetch_world_bank, COUNTRY_CODES
from sources.numbeo import fetch_country_indices as fetch_numbeo
from normalize import (
    norm_stability, norm_rule_of_law, norm_corruption,
    norm_gdp_pc, norm_unemployment, norm_pop_density,
    norm_food, norm_life_exp, norm_internet, norm_health_exp,
    norm_homicide, norm_military_exp,
    norm_numbeo_crime, norm_numbeo_safety, norm_numbeo_healthcare, norm_numbeo_cost,
)

DATA_DIR = Path(__file__).parent
CACHE_DIR = DATA_DIR / "cache"
MANUAL_PATH = DATA_DIR / "manual_data.json"
WB_CACHE = CACHE_DIR / "world_bank.json"
NUMBEO_CACHE = CACHE_DIR / "numbeo.json"
INDEX_HTML = DATA_DIR.parent / "index.html"

CACHE_TTL_DAYS = 7

# Country names (for JS output)
COUNTRY_NAMES = {
    "840": ("United States", "Americas"), "124": ("Canada", "Americas"),
    "036": ("Australia", "Oceania"), "554": ("New Zealand", "Oceania"),
    "356": ("India", "Asia"), "156": ("China", "Asia"),
    "643": ("Russia", "Europe"), "076": ("Brazil", "Americas"),
    "276": ("Germany", "Europe"), "250": ("France", "Europe"),
    "826": ("United Kingdom", "Europe"), "380": ("Italy", "Europe"),
    "724": ("Spain", "Europe"), "620": ("Portugal", "Europe"),
    "528": ("Netherlands", "Europe"), "752": ("Sweden", "Europe"),
    "578": ("Norway", "Europe"), "208": ("Denmark", "Europe"),
    "246": ("Finland", "Europe"), "756": ("Switzerland", "Europe"),
    "040": ("Austria", "Europe"), "203": ("Czech Republic", "Europe"),
    "703": ("Slovakia", "Europe"), "705": ("Slovenia", "Europe"),
    "191": ("Croatia", "Europe"), "348": ("Hungary", "Europe"),
    "616": ("Poland", "Europe"), "642": ("Romania", "Europe"),
    "100": ("Bulgaria", "Europe"), "300": ("Greece", "Europe"),
    "233": ("Estonia", "Europe"), "428": ("Latvia", "Europe"),
    "440": ("Lithuania", "Europe"), "372": ("Ireland", "Europe"),
    "442": ("Luxembourg", "Europe"), "352": ("Iceland", "Europe"),
    "792": ("Turkey", "Middle East"), "804": ("Ukraine", "Europe"),
    "112": ("Belarus", "Europe"), "498": ("Moldova", "Europe"),
    "688": ("Serbia", "Europe"), "376": ("Israel", "Middle East"),
    "364": ("Iran", "Middle East"), "784": ("UAE", "Middle East"),
    "682": ("Saudi Arabia", "Middle East"), "400": ("Jordan", "Middle East"),
    "422": ("Lebanon", "Middle East"), "818": ("Egypt", "Africa"),
    "504": ("Morocco", "Africa"), "788": ("Tunisia", "Africa"),
    "012": ("Algeria", "Africa"), "710": ("South Africa", "Africa"),
    "404": ("Kenya", "Africa"), "410": ("South Korea", "Asia"),
    "392": ("Japan", "Asia"), "702": ("Singapore", "Asia"),
    "458": ("Malaysia", "Asia"), "764": ("Thailand", "Asia"),
    "704": ("Vietnam", "Asia"), "360": ("Indonesia", "Asia"),
    "608": ("Philippines", "Asia"), "398": ("Kazakhstan", "Asia"),
    "496": ("Mongolia", "Asia"), "268": ("Georgia", "Asia"),
    "051": ("Armenia", "Asia"), "586": ("Pakistan", "Asia"),
    "050": ("Bangladesh", "Asia"), "484": ("Mexico", "Americas"),
    "170": ("Colombia", "Americas"), "604": ("Peru", "Americas"),
    "032": ("Argentina", "Americas"), "152": ("Chile", "Americas"),
    "858": ("Uruguay", "Americas"), "068": ("Bolivia", "Americas"),
    "218": ("Ecuador", "Americas"), "600": ("Paraguay", "Americas"),
    "188": ("Costa Rica", "Americas"), "591": ("Panama", "Americas"),
    "192": ("Cuba", "Americas"), "214": ("Dominican Republic", "Americas"),
    "566": ("Nigeria", "Africa"), "231": ("Ethiopia", "Africa"),
}


def is_cache_fresh(path: Path, ttl_days: int = CACHE_TTL_DAYS) -> bool:
    if not path.exists():
        return False
    age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
    return age < timedelta(days=ttl_days)


def load_json(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def get_world_bank_data(force_refresh: bool) -> dict:
    if not force_refresh and is_cache_fresh(WB_CACHE):
        print(f"Using cached World Bank data ({WB_CACHE.name})")
        return load_json(WB_CACHE)
    print("Fetching World Bank data...")
    return fetch_world_bank(cache_path=str(WB_CACHE))


def get_numbeo_data(api_key: str, force_refresh: bool) -> dict:
    if not api_key:
        if NUMBEO_CACHE.exists():
            print(f"Using cached Numbeo data ({NUMBEO_CACHE.name})")
            return load_json(NUMBEO_CACHE)
        return {}
    if not force_refresh and is_cache_fresh(NUMBEO_CACHE):
        print(f"Using cached Numbeo data ({NUMBEO_CACHE.name})")
        return load_json(NUMBEO_CACHE)
    print("Fetching Numbeo data...")
    return fetch_numbeo(api_key=api_key, cache_path=str(NUMBEO_CACHE))


def build_scores(wb: dict, numbeo: dict, manual: dict) -> dict:
    """Combine all sources into final 1-10 scores per country."""
    scores = {}

    for numeric in COUNTRY_CODES:
        w = wb.get(numeric, {})
        n = numbeo.get(numeric, {})
        m = manual.get(numeric, {})

        def pick(*vals):
            """Return first non-None value, rounded to 1 decimal."""
            for v in vals:
                if v is not None:
                    return round(float(v), 1)
            return None

        # ── Governance / Stability ──────────────────────────────────────────
        gov_components = [
            norm_stability(w.get("stability")),
            norm_rule_of_law(w.get("rule_of_law")),
            norm_corruption(w.get("corruption")),
        ]
        gov_vals = [v for v in gov_components if v is not None]
        stability = round(sum(gov_vals) / len(gov_vals), 1) if gov_vals else None

        # ── Economy ────────────────────────────────────────────────────────
        economy = norm_gdp_pc(w.get("gdp_pc"))

        # ── Employment ─────────────────────────────────────────────────────
        employment = norm_unemployment(w.get("unemployment"))

        # ── Population Density ─────────────────────────────────────────────
        density = norm_pop_density(w.get("pop_density"))

        # ── Food Security ──────────────────────────────────────────────────
        food = norm_food(w.get("food_idx"))

        # ── Technology ─────────────────────────────────────────────────────
        tech = norm_internet(w.get("internet"))

        # ── Healthcare ─────────────────────────────────────────────────────
        # Prefer Numbeo Healthcare Index; fall back to life expectancy proxy
        if n.get("health_care_index") is not None:
            health = norm_numbeo_healthcare(n["health_care_index"])
        elif w.get("life_exp") is not None:
            health = norm_life_exp(w["life_exp"])
        else:
            health = None

        # ── Safety / Crime ─────────────────────────────────────────────────
        if n.get("safety_index") is not None:
            safety = norm_numbeo_safety(n["safety_index"])
        elif w.get("homicide") is not None:
            safety = norm_homicide(w["homicide"])
        else:
            safety = None

        # ── Cost of Living ─────────────────────────────────────────────────
        if n.get("cost_of_living_index") is not None:
            cost = norm_numbeo_cost(n["cost_of_living_index"])
        else:
            cost = None  # no good free API fallback

        # ── Military (proxy: expenditure % GDP) ───────────────────────────
        military = norm_military_exp(w.get("military_exp"))

        # ── Terrorism: no free API → use manual if available ───────────────
        terrorism = m.get("terrorism")  # set manually from GPI CSV if loaded

        scores[numeric] = {
            # Auto-sourced
            "stability":  stability,
            "economy":    economy,
            "employment": employment,
            "density":    density,
            "food":       food,
            "tech":       tech,
            "health":     health,
            "safety":     safety,
            "cost":       cost,
            "military":   military,
            # Manual
            "nuclear":    m.get("nuclear"),
            "geography":  m.get("geography"),
            "neighbors":  m.get("neighbors"),
            "immigration":m.get("immigration"),
            "resource":   m.get("resource"),
            "climate":    m.get("climate"),
            "crypto":     m.get("crypto"),
            "taxes":      m.get("taxes"),
            "business":   m.get("business"),
            "terrorism":  terrorism,
        }

    return scores


def scores_to_js(scores: dict) -> str:
    """Generate the COUNTRIES JS object literal."""
    lines = []
    lines.append("// ─── DATA ────────────────────────────────────────────────────────────────────")
    lines.append("// Auto-generated by safe-map/data/update.py")
    lines.append(f"// Sources: World Bank API, Numbeo API, manual_data.json")
    lines.append(f"// Updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("// Params: food, resource, military, nuclear, tech, climate, geography, neighbors,")
    lines.append("//         stability, terrorism, immigration, cost, economy, density,")
    lines.append("//         employment, business, taxes, crypto, safety, health")
    lines.append("const COUNTRIES = {")

    for numeric, s in scores.items():
        name, region = COUNTRY_NAMES.get(numeric, ("Unknown", "Unknown"))

        def fmt(v, fallback=5):
            if v is None:
                return fallback
            return round(float(v), 1)

        line = (
            f"  '{numeric}': {{ name:'{name}', region:'{region}', "
            f"food:{fmt(s['food'])}, resource:{fmt(s['resource'])}, "
            f"military:{fmt(s['military'])}, nuclear:{fmt(s['nuclear'])}, "
            f"tech:{fmt(s['tech'])}, climate:{fmt(s['climate'])}, "
            f"geography:{fmt(s['geography'])}, neighbors:{fmt(s['neighbors'])}, "
            f"stability:{fmt(s['stability'])}, terrorism:{fmt(s['terrorism'])}, "
            f"immigration:{fmt(s['immigration'])}, cost:{fmt(s['cost'])}, "
            f"economy:{fmt(s['economy'])}, density:{fmt(s['density'])}, "
            f"employment:{fmt(s['employment'])}, business:{fmt(s['business'])}, "
            f"taxes:{fmt(s['taxes'])}, crypto:{fmt(s['crypto'])}, "
            f"safety:{fmt(s['safety'])}, health:{fmt(s['health'])} }},"
        )
        lines.append(line)

    lines.append("};")
    return "\n".join(lines)


def inject_into_html(js_block: str, html_path: Path):
    """Replace the COUNTRIES block in index.html with fresh data."""
    content = html_path.read_text(encoding="utf-8")

    # Match from the auto-gen comment (or fallback to old comment) to closing };
    pattern = r"(// ─── DATA ─+.*?\nconst COUNTRIES = \{.*?\n\};)"
    replacement = js_block

    new_content, n = re.subn(pattern, replacement, content, flags=re.DOTALL)
    if n == 0:
        print("ERROR: Could not find COUNTRIES block in index.html")
        print("Run this script once manually and paste the output.")
        return False

    html_path.write_text(new_content, encoding="utf-8")
    print(f"Injected into {html_path}")
    return True


def print_coverage_report(scores: dict):
    """Show how many countries got auto vs manual data."""
    auto_params = ["stability", "economy", "employment", "density", "food", "tech", "health", "safety", "cost", "military"]
    total = len(scores)
    print("\n── Coverage Report ─────────────────────────────────────────────")
    for param in auto_params:
        filled = sum(1 for s in scores.values() if s.get(param) is not None)
        pct = filled / total * 100
        bar = "█" * int(pct / 5)
        print(f"  {param:12s} {filled:3d}/{total} ({pct:5.1f}%) {bar}")
    print("────────────────────────────────────────────────────────────────")


def main():
    parser = argparse.ArgumentParser(description="Update Safe Harbor Index data")
    parser.add_argument("--refresh", action="store_true", help="Force re-fetch (ignore cache)")
    parser.add_argument("--numbeo-key", metavar="KEY", help="Numbeo API key")
    parser.add_argument("--dry-run", action="store_true", help="Print JS, don't write HTML")
    args = parser.parse_args()

    CACHE_DIR.mkdir(exist_ok=True)

    print("=== Safe Harbor Index — Data Update ===\n")

    # 1. Fetch data
    wb_data = get_world_bank_data(args.refresh)
    numbeo_data = get_numbeo_data(args.numbeo_key, args.refresh)
    manual_data = load_json(MANUAL_PATH)

    print(f"\nLoaded: {len(wb_data)} countries from World Bank")
    print(f"Loaded: {len(numbeo_data)} countries from Numbeo")
    print(f"Loaded: {len([k for k in manual_data if not k.startswith('_')])} countries from manual data\n")

    # 2. Build scores
    scores = build_scores(wb_data, numbeo_data, manual_data)
    print_coverage_report(scores)

    # 3. Generate JS
    js_block = scores_to_js(scores)

    if args.dry_run:
        print("\n── Generated JS (dry run) ──────────────────────────────────────")
        print(js_block[:2000], "...\n")
        return

    # 4. Inject into HTML
    print(f"\nInjecting into {INDEX_HTML}...")
    success = inject_into_html(js_block, INDEX_HTML)

    if success:
        print("\nDone! Run: git diff safe-map/index.html to review changes.")


if __name__ == "__main__":
    main()
