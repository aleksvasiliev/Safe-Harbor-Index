"""
Normalization functions: raw API values → 1-10 scores.
Each function is documented with the raw range and transformation logic.
"""

import math


def clamp(val, lo=1.0, hi=10.0):
    return max(lo, min(hi, val))


def linear(val, raw_min, raw_max, invert=False):
    """Linear normalization to 1-10."""
    if val is None:
        return None
    ratio = (val - raw_min) / (raw_max - raw_min)
    if invert:
        ratio = 1.0 - ratio
    return clamp(round(ratio * 9 + 1, 1))


def log_scale(val, raw_min, raw_max, invert=False):
    """Log normalization — useful for GDP, density (skewed distributions)."""
    if val is None or val <= 0:
        return None
    log_val = math.log(max(val, raw_min))
    log_min = math.log(raw_min)
    log_max = math.log(raw_max)
    ratio = (log_val - log_min) / (log_max - log_min)
    if invert:
        ratio = 1.0 - ratio
    return clamp(round(ratio * 9 + 1, 1))


# ── Per-indicator normalizers ─────────────────────────────────────────────────

def norm_stability(val):
    """World Bank PV.EST: -2.5 (worst) to +2.5 (best)"""
    return linear(val, -2.5, 2.0)

def norm_rule_of_law(val):
    """World Bank RL.EST: -2.5 to +2.0"""
    return linear(val, -2.5, 2.0)

def norm_corruption(val):
    """World Bank CC.EST: -2.5 to +2.0"""
    return linear(val, -2.5, 2.0)

def norm_gdp_pc(val):
    """GDP per capita USD: log scale, $500–$120,000"""
    return log_scale(val, 500, 120000)

def norm_unemployment(val):
    """Unemployment %: 0–30%, inverted (lower = better)"""
    return linear(val, 0, 30, invert=True)

def norm_pop_density(val):
    """Population density (ppl/km²): log scale, inverted (lower = better for resilience)"""
    return log_scale(val, 1, 2000, invert=True)

def norm_food(val):
    """Food Production Index (2014-2016=100): range 40–200"""
    return linear(val, 40, 200)

def norm_life_exp(val):
    """Life expectancy years: 45–85"""
    return linear(val, 45, 85)

def norm_internet(val):
    """Internet users %: 0–100 → tech proxy"""
    return linear(val, 0, 100)

def norm_health_exp(val):
    """Health expenditure % GDP: 1–12% — higher spending → better system (proxy)"""
    return linear(val, 1, 12)

def norm_homicide(val):
    """Intentional homicides per 100k: 0–80, inverted (lower = safer)"""
    return linear(val, 0, 50, invert=True)

def norm_military_exp(val):
    """Military expenditure % GDP: 0–6% — proxy for commitment, not capability"""
    return linear(val, 0, 6)

# Numbeo indices are already 0-100 scales
def norm_numbeo_crime(val):
    """Numbeo Crime Index 0-100: invert (lower crime = higher score)"""
    return linear(val, 0, 100, invert=True)

def norm_numbeo_safety(val):
    """Numbeo Safety Index 0-100: direct"""
    return linear(val, 0, 100)

def norm_numbeo_healthcare(val):
    """Numbeo Healthcare Index 0-100: direct"""
    return linear(val, 0, 100)

def norm_numbeo_cost(val):
    """Numbeo Cost of Living Index 0-100+: invert (lower cost = higher score)"""
    return linear(val, 0, 120, invert=True)
