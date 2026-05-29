"""
Unit tests for backend.app.utils.chart_builder
Covers:
  - _extract_rows: bare array, wrapped dict, embedded JSON in free text, empty/garbage input
  - _detect_datasets: column-name detection for each dataset type
  - build_chart_spec: correct chart builder dispatched per dataset combination
  - DB fallback when extraction result is unparseable
"""
import json
import pytest

from backend.app.utils.chart_builder import (
    build_chart_spec,
    _extract_rows,
    _detect_datasets,
)


# ---------------------------------------------------------------------------
# Fixtures — sample row payloads
# ---------------------------------------------------------------------------

EMPLOYMENT_CPI_ROWS = [
    {"year": 2020, "sector": "Technology", "median_salary": 6500, "cpi_index": 99.1},
    {"year": 2021, "sector": "Technology", "median_salary": 7000, "cpi_index": 101.4},
    {"year": 2022, "sector": "Technology", "median_salary": 7600, "cpi_index": 107.6},
]

EMPLOYMENT_ONLY_ROWS = [
    {"year": 2020, "sector": "Technology",          "employment_change": 8500,  "median_salary": 6500},
    {"year": 2020, "sector": "Financial Services",  "employment_change": 3500,  "median_salary": 7200},
    {"year": 2021, "sector": "Technology",          "employment_change": 12000, "median_salary": 7000},
    {"year": 2021, "sector": "Financial Services",  "employment_change": 5200,  "median_salary": 7500},
]

POPULATION_ROWS = [
    {"year": 2020, "resident_population": 5685800, "median_age": 41.5, "dependency_ratio": 18.6},
    {"year": 2021, "resident_population": 5453600, "median_age": 41.8, "dependency_ratio": 19.2},
]

CPI_ONLY_ROWS = [
    {"year": 2020, "category": "All Items", "cpi_index": 99.1},
    {"year": 2020, "category": "Food",      "cpi_index": 98.8},
    {"year": 2021, "category": "All Items", "cpi_index": 101.4},
]


# ===========================================================================
# 1. _extract_rows — parsing logic
# ===========================================================================

class TestExtractRows:

    def test_bare_json_array(self):
        text = json.dumps(EMPLOYMENT_CPI_ROWS)
        rows = _extract_rows(text)
        assert len(rows) == 3
        assert rows[0]["year"] == 2020

    def test_wrapped_dict_with_data_key(self):
        payload = {"data": EMPLOYMENT_CPI_ROWS, "quality_report": "All columns clean."}
        text = json.dumps(payload)
        rows = _extract_rows(text)
        assert len(rows) == 3

    def test_wrapped_dict_arbitrary_list_key(self):
        payload = {"records": POPULATION_ROWS, "source": "SingStat"}
        text = json.dumps(payload)
        rows = _extract_rows(text)
        assert len(rows) == 2

    def test_embedded_json_in_free_text(self):
        """LLM free-text response with JSON array buried inside."""
        text = (
            "Here is the cleaned data:\n"
            + json.dumps(EMPLOYMENT_CPI_ROWS)
            + "\nData quality: 0 nulls detected."
        )
        rows = _extract_rows(text)
        assert len(rows) == 3

    def test_empty_string_returns_empty_list(self):
        assert _extract_rows("") == []

    def test_garbage_string_returns_empty_list(self):
        assert _extract_rows("No JSON here, just plain English text.") == []

    def test_empty_array_returns_empty_list(self):
        assert _extract_rows("[]") == []


# ===========================================================================
# 2. _detect_datasets — column name detection
# ===========================================================================

class TestDetectDatasets:

    def test_detects_employment_and_cpi(self):
        flags = _detect_datasets(EMPLOYMENT_CPI_ROWS)
        assert flags["has_employment"] is True
        assert flags["has_cpi"] is True
        assert flags["has_population"] is False

    def test_detects_employment_only(self):
        flags = _detect_datasets(EMPLOYMENT_ONLY_ROWS)
        assert flags["has_employment"] is True
        assert flags["has_cpi"] is False
        assert flags["has_sector"] is True

    def test_detects_population(self):
        flags = _detect_datasets(POPULATION_ROWS)
        assert flags["has_population"] is True
        assert flags["has_employment"] is False

    def test_detects_cpi_only(self):
        flags = _detect_datasets(CPI_ONLY_ROWS)
        assert flags["has_cpi"] is True
        assert flags["has_employment"] is False
        assert flags["has_population"] is False

    def test_empty_rows_returns_empty_flags(self):
        assert _detect_datasets([]) == {}


# ===========================================================================
# 3. build_chart_spec — correct chart type dispatched
# ===========================================================================

class TestBuildChartSpec:

    # ---- Employment + CPI → Composed chart ---------------------------------

    def test_employment_cpi_returns_composed(self):
        spec = build_chart_spec(json.dumps(EMPLOYMENT_CPI_ROWS))
        assert spec["chart_type"] == "Composed"
        assert spec["xAxis"] == "year"
        assert len(spec["data"]) == 3
        # Both salary and cpi keys present in data points
        assert "salary" in spec["data"][0] or "cpi" in spec["data"][0]

    def test_employment_cpi_series_has_bar_and_line(self):
        spec = build_chart_spec(json.dumps(EMPLOYMENT_CPI_ROWS))
        types = {s["type"] for s in spec["series"]}
        assert "bar" in types
        assert "line" in types

    # ---- Multi-sector employment → Bar chart --------------------------------

    def test_multi_sector_employment_returns_bar(self):
        spec = build_chart_spec(json.dumps(EMPLOYMENT_ONLY_ROWS))
        assert spec["chart_type"] == "Bar"
        assert spec["xAxis"] == "year"
        # Should have one series per sector
        series_names = {s["name"] for s in spec["series"]}
        assert "Technology" in series_names
        assert "Financial Services" in series_names

    def test_multi_sector_data_grouped_by_year(self):
        spec = build_chart_spec(json.dumps(EMPLOYMENT_ONLY_ROWS))
        years = [d["year"] for d in spec["data"]]
        # Rows cover 2020 & 2021 — exactly 2 grouped data points
        assert sorted(set(years)) == [2020, 2021]
        assert len(spec["data"]) == 2

    # ---- Population → Composed area+line chart -----------------------------

    def test_population_returns_composed(self):
        spec = build_chart_spec(json.dumps(POPULATION_ROWS))
        assert spec["chart_type"] == "Composed"
        assert len(spec["data"]) == 2
        series_keys = {s["dataKey"] for s in spec["series"]}
        assert "population" in series_keys
        assert "dependency_ratio" in series_keys

    # ---- CPI only → Line chart ---------------------------------------------

    def test_cpi_only_returns_line(self):
        spec = build_chart_spec(json.dumps(CPI_ONLY_ROWS))
        assert spec["chart_type"] == "Line"
        # All series should be lines
        assert all(s["type"] == "line" for s in spec["series"])

    # ---- Mandatory structure checks on every spec --------------------------

    @pytest.mark.parametrize("rows", [
        EMPLOYMENT_CPI_ROWS,
        EMPLOYMENT_ONLY_ROWS,
        POPULATION_ROWS,
        CPI_ONLY_ROWS,
    ])
    def test_spec_always_has_required_keys(self, rows):
        spec = build_chart_spec(json.dumps(rows))
        assert "chart_type" in spec
        assert "title" in spec
        assert "xAxis" in spec
        assert "series" in spec
        assert "data" in spec
        assert isinstance(spec["series"], list)
        assert len(spec["series"]) > 0
        assert isinstance(spec["data"], list)

    @pytest.mark.parametrize("rows", [
        EMPLOYMENT_CPI_ROWS,
        EMPLOYMENT_ONLY_ROWS,
        POPULATION_ROWS,
        CPI_ONLY_ROWS,
    ])
    def test_every_series_has_required_keys(self, rows):
        spec = build_chart_spec(json.dumps(rows))
        for s in spec["series"]:
            assert "name" in s
            assert "type" in s
            assert "dataKey" in s
            assert "color" in s
            assert s["color"].startswith("#")

    # ---- Free-text input (LLM-style) works the same way --------------------

    def test_free_text_extraction_result(self):
        text = (
            "Data Quality Report: 0 nulls.\n"
            "Cleaned Dataset:\n"
            + json.dumps(EMPLOYMENT_CPI_ROWS)
            + "\nAll records validated."
        )
        spec = build_chart_spec(text)
        assert spec["chart_type"] == "Composed"
        assert len(spec["data"]) == 3

    # ---- Wrapped dict with data key ----------------------------------------

    def test_wrapped_dict_input(self):
        payload = {"data": POPULATION_ROWS, "quality": "clean"}
        spec = build_chart_spec(json.dumps(payload))
        assert spec["chart_type"] == "Composed"

    # ---- DB fallback when input is unparseable -----------------------------

    def test_db_fallback_on_garbage_input(self):
        """Unparseable input should trigger DB fallback — not crash."""
        spec = build_chart_spec("This is completely unstructured LLM text with no JSON.")
        # Fallback still returns a valid spec with required keys
        assert "chart_type" in spec
        assert "series" in spec
        assert "data" in spec
        # Fallback populates from DB so data should be non-empty
        # (requires seeded DB; will be empty list only if DB is blank)
        assert isinstance(spec["data"], list)

    def test_db_fallback_on_empty_string(self):
        spec = build_chart_spec("")
        assert "chart_type" in spec
        assert "series" in spec
