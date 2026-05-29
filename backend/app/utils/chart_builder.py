import json
import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger("ChartBuilder")

# ---------------------------------------------------------------------------
# Colour palette — reused across all chart series
# ---------------------------------------------------------------------------
PALETTE = ["#6366f1", "#f43f5e", "#10b981", "#f59e0b", "#3b82f6", "#ec4899"]


def _try_parse_json_blocks(text: str) -> List[Any]:
    """Extract all valid JSON arrays or objects embedded inside a free-text string."""
    results = []
    # Match top-level arrays first, then objects
    for pattern in [r"\[[\s\S]+?\]", r"\{[\s\S]+?\}"]:
        for match in re.finditer(pattern, text):
            try:
                results.append(json.loads(match.group()))
            except Exception:
                continue
    return results


def _extract_rows(extraction_result: str) -> List[Dict]:
    """
    Best-effort parse of ExtractionAgent's FINAL_ANSWER into a flat list of dicts.
    Handles:
      - A bare JSON array of objects
      - A JSON object with a list value (e.g. {"data": [...], "quality": ...})
      - Free text containing embedded JSON arrays
    """
    text = extraction_result.strip()

    # Direct parse attempt
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            # Look for the first list value
            for v in parsed.values():
                if isinstance(v, list) and v:
                    return v
    except Exception:
        pass

    # Fallback: scan for any JSON array in the text
    for candidate in _try_parse_json_blocks(text):
        if isinstance(candidate, list) and candidate and isinstance(candidate[0], dict):
            return candidate

    return []


def _detect_datasets(rows: List[Dict]) -> Dict[str, bool]:
    """Inspect row keys to identify which datasets are present."""
    if not rows:
        return {}
    keys = set(rows[0].keys())
    return {
        "has_employment": "median_salary" in keys or "employment_change" in keys,
        "has_cpi": "cpi_index" in keys or "cpi" in keys,
        "has_population": "resident_population" in keys or "median_age" in keys,
        "has_year": "year" in keys,
        "has_sector": "sector" in keys,
    }


# ---------------------------------------------------------------------------
# Chart spec builders — one per logical dataset combination
# ---------------------------------------------------------------------------

def _build_employment_cpi_chart(rows: List[Dict]) -> Dict:
    """Salary vs CPI composed chart — most common query type."""
    data = []
    for r in rows:
        point = {"year": r.get("year")}
        # Salary key normalisation
        for k in ("median_salary", "salary"):
            if k in r:
                point["salary"] = r[k]
                break
        # CPI key normalisation
        for k in ("cpi_index", "cpi"):
            if k in r:
                point["cpi"] = r[k]
                break
        if len(point) > 1:
            data.append(point)

    return {
        "chart_type": "Composed",
        "title": "Median Salary vs CPI Inflation",
        "xAxis": "year",
        "series": [
            {"name": "Median Salary (SGD)", "type": "bar",  "dataKey": "salary", "color": PALETTE[0], "yAxisId": "left"},
            {"name": "CPI Index",           "type": "line", "dataKey": "cpi",    "color": PALETTE[1], "yAxisId": "right"},
        ],
        "data": data,
    }


def _build_employment_chart(rows: List[Dict], sectors: List[str]) -> Dict:
    """Multi-sector employment change bar chart."""
    # Group by year → one data point per year, one series per sector
    years_map: Dict[int, Dict] = {}
    for r in rows:
        yr = r.get("year")
        if yr is None:
            continue
        if yr not in years_map:
            years_map[yr] = {"year": yr}
        sector = r.get("sector", "Unknown")
        safe_key = sector.replace(" ", "_").replace("&", "and").lower()
        years_map[yr][safe_key] = r.get("employment_change", r.get("median_salary"))

    data = [years_map[yr] for yr in sorted(years_map)]
    series = []
    for idx, sector in enumerate(sectors):
        safe_key = sector.replace(" ", "_").replace("&", "and").lower()
        series.append({
            "name": sector,
            "type": "bar",
            "dataKey": safe_key,
            "color": PALETTE[idx % len(PALETTE)],
        })

    return {
        "chart_type": "Bar",
        "title": "Employment Change by Sector",
        "xAxis": "year",
        "series": series,
        "data": data,
    }


def _build_population_chart(rows: List[Dict]) -> Dict:
    """Population trend with dependency ratio line."""
    data = [
        {
            "year": r.get("year"),
            "population": r.get("resident_population"),
            "dependency_ratio": r.get("dependency_ratio"),
            "median_age": r.get("median_age"),
        }
        for r in rows
    ]
    return {
        "chart_type": "Composed",
        "title": "Singapore Resident Population & Dependency Ratio",
        "xAxis": "year",
        "series": [
            {"name": "Resident Population", "type": "area", "dataKey": "population",       "color": PALETTE[2], "yAxisId": "left"},
            {"name": "Dependency Ratio",    "type": "line", "dataKey": "dependency_ratio", "color": PALETTE[1], "yAxisId": "right"},
        ],
        "data": data,
    }


def _build_cpi_chart(rows: List[Dict]) -> Dict:
    """CPI trend line chart (may have multiple categories)."""
    categories = list({r.get("category", "All Items") for r in rows})
    years_map: Dict[int, Dict] = {}
    for r in rows:
        yr = r.get("year")
        if yr is None:
            continue
        if yr not in years_map:
            years_map[yr] = {"year": yr}
        cat = r.get("category", "All Items")
        safe_key = cat.replace(" ", "_").lower()
        # Average across months if multiple rows per year+category
        existing = years_map[yr].get(safe_key)
        val = r.get("cpi_index", r.get("cpi"))
        if existing is None:
            years_map[yr][safe_key] = val
        elif val is not None:
            years_map[yr][safe_key] = round((existing + val) / 2, 2)

    data = [years_map[yr] for yr in sorted(years_map)]
    series = [
        {"name": cat, "type": "line", "dataKey": cat.replace(" ", "_").lower(), "color": PALETTE[idx % len(PALETTE)]}
        for idx, cat in enumerate(categories)
    ]
    return {
        "chart_type": "Line",
        "title": "Consumer Price Index (CPI) Trends",
        "xAxis": "year",
        "series": series,
        "data": data,
    }


# ---------------------------------------------------------------------------
# DB fallback — query fresh data when extraction result cannot be parsed
# ---------------------------------------------------------------------------

def _db_fallback_chart() -> Dict:
    """Directly query DB for a standard Tech-sector salary vs CPI chart."""
    from backend.app.database import SessionLocal
    from backend.app.models import MOMEmployment, SingStatCPI

    db = SessionLocal()
    data = []
    try:
        tech = db.query(MOMEmployment).filter(MOMEmployment.sector == "Technology").order_by(MOMEmployment.year).all()
        cpi  = db.query(SingStatCPI).filter(SingStatCPI.category == "All Items", SingStatCPI.month == "Jun").order_by(SingStatCPI.year).all()
        cpi_map = {c.year: c.cpi_index for c in cpi}
        for t in tech:
            data.append({
                "year":         t.year,
                "salary":       t.median_salary,
                "change":       t.employment_change,
                "unemployment": t.unemployment_rate,
                "cpi":          cpi_map.get(t.year, 100.0),
            })
    except Exception as e:
        logger.error(f"DB fallback chart query failed: {e}")
    finally:
        db.close()

    return {
        "chart_type": "Composed",
        "title":      "Tech Sector Salaries vs CPI Inflation Trends",
        "xAxis":      "year",
        "series": [
            {"name": "Median Salary (SGD)", "type": "bar",  "dataKey": "salary", "color": PALETTE[0], "yAxisId": "left"},
            {"name": "CPI (All Items)",     "type": "line", "dataKey": "cpi",    "color": PALETTE[1], "yAxisId": "right"},
        ],
        "data": data,
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_chart_spec(extraction_result: str, user_query: str = "") -> Dict:
    """
    Deterministically build a chart spec from the ExtractionAgent's result string.

    Strategy:
      1. Parse rows out of extraction_result (JSON or embedded JSON).
      2. Detect which datasets are present from column names.
      3. Select the most appropriate chart builder.
      4. Fall back to a fresh DB query if parsing fails.

    No LLM involvement — purely programmatic.
    """
    logger.info("📊 ChartBuilder: building chart spec from extraction result...")
    rows = _extract_rows(extraction_result)

    if not rows:
        logger.warning("📊 ChartBuilder: could not parse rows from extraction result. Using DB fallback.")
        return _db_fallback_chart()

    flags = _detect_datasets(rows)
    logger.info(f"📊 ChartBuilder: detected dataset flags: {flags}")

    has_employment  = flags.get("has_employment", False)
    has_cpi         = flags.get("has_cpi", False)
    has_population  = flags.get("has_population", False)
    has_sector      = flags.get("has_sector", False)

    # Priority 1 — employment + CPI combined (most common salary analysis)
    if has_employment and has_cpi:
        return _build_employment_cpi_chart(rows)

    # Priority 2 — multi-sector employment breakdown
    if has_employment and has_sector:
        sectors = list({r.get("sector", "Unknown") for r in rows if r.get("sector")})
        return _build_employment_chart(rows, sectors)

    # Priority 3 — salary-only employment chart
    if has_employment:
        return _build_employment_chart(rows, ["All Sectors"])

    # Priority 4 — population demographics
    if has_population:
        return _build_population_chart(rows)

    # Priority 5 — CPI-only
    if has_cpi:
        return _build_cpi_chart(rows)

    # Final fallback
    logger.warning("📊 ChartBuilder: no known dataset detected in rows. Using DB fallback.")
    return _db_fallback_chart()
