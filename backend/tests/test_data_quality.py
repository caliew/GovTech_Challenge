import pytest
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal, Base, engine
from backend.app.utils.validator import HallucinationDetector
from backend.app.models import MOMEmployment, SingStatPopulation

@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. UNIT TEST: Numerical Extraction and String Normalization
def test_numerical_extraction():
    # Simple digits
    assert HallucinationDetector.extract_numbers_from_text("42") == [42.0]
    # Decimals
    assert HallucinationDetector.extract_numbers_from_text("3.14159") == [3.14159]
    # Comma separation and currency markers
    text_currency = "The salary was $8,250.50 in 2024."
    extracted = HallucinationDetector.extract_numbers_from_text(text_currency.replace(",", ""))
    assert 8250.50 in extracted

# 2. UNIT TEST: Table Parser Resiliency (Malformed Tables)
def test_markdown_table_parser():
    # Extra spacing and uneven dividers
    raw_markdown = """
| Year | Sector | Median Monthly Salary (SGD) |
|:---|:---:|---:|
|   2020   |  Technology | $6,500 |
| 2021 | Finance | $7,500 |
"""
    tables = HallucinationDetector.parse_markdown_tables(raw_markdown)
    assert len(tables) == 1
    rows = tables[0]
    assert len(rows) == 2
    assert rows[0]["Year"] == "2020"
    assert rows[0]["Sector"] == "Technology"
    assert rows[0]["Median Monthly Salary (SGD)"] == "$6,500"

    # Missing headers / empty strings should bypass gracefully
    bad_markdown = "Just general sentences, no table syntax | whatsoever |"
    assert HallucinationDetector.parse_markdown_tables(bad_markdown) == []

# 3. UNIT TEST: Tolerance Limits and Factual Consistency
def test_validation_tolerance(db_session):
    # Accurate database facts for 2020 Tech Salary is $6,500, Population is 5,685,800
    # Let's test a minor rounding within the 2% tolerance threshold (e.g. 5.69M resident pop)
    # 5.69M / 5,685,800 is a 0.07% deviation (well below 2%)
    rounded_markdown = """
| Year | Median Monthly Salary (SGD) | Resident Population |
| :--- | :-------------------------: | :-----------------: |
| 2020 | $6,500                      | 5.69M               |
"""
    report = HallucinationDetector.validate_report(rounded_markdown, db_session)
    assert report["status"] == "success"
    assert report["mismatches_count"] == 0
    assert report["accuracy_score"] == 1.0

    # Let's test a minor rounding in tech salary which expects strict exact matching
    # Since salary compares floats directly with strict tolerance (report_val - fact_val > 0.01),
    # changing $6,500 to $6,501 must trigger a mismatch.
    slight_wage_mismatch = """
| Year | Median Monthly Salary (SGD) | Resident Population |
| :--- | :-------------------------: | :-----------------: |
| 2020 | $6,501                      | 5,685,800           |
"""
    report_wage = HallucinationDetector.validate_report(slight_wage_mismatch, db_session)
    assert report_wage["mismatches_count"] == 1
    assert "Salary" in report_wage["mismatches"][0]["entity"]

# 4. UNIT TEST: Anomaly and Out-Of-Bounds Heuristics
def test_anomaly_out_of_bounds_detection(db_session):
    # Standard query with reasonable statements passes without quality warning
    clean_markdown = "The unemployment rate in the healthcare sector remained stable at 1.2% during peak periods."
    report_clean = HallucinationDetector.validate_report(clean_markdown, db_session)
    assert report_clean["mismatches_count"] == 0

    # Anomaly statement claiming extreme unemployment rates (e.g. 15.4% during pandemic) triggers out-of-bounds mismatch
    anomaly_markdown = "Due to the economic downturn, structural tech sector unemployment rates soared to a record 15.4% in 2023."
    report_anomaly = HallucinationDetector.validate_report(anomaly_markdown, db_session)
    
    assert report_anomaly["mismatches_count"] == 1
    mismatch = report_anomaly["mismatches"][0]
    assert "Anomaly detection" in mismatch["entity"]
    assert mismatch["reported_value"] == "15.4%"
    assert mismatch["source"] == "Heuristic Out-Of-Bounds check"
