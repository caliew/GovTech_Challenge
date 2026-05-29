import pytest
import json
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal, Base, engine
from backend.app.models import MOMEmployment, SingStatPopulation, SingStatCPI
from backend.app.tools.db_tools import execute_sql_query, get_database_schema
from backend.app.tools.math_tools import calculate_correlation, calculate_growth_rate
from backend.app.utils.llm import llm_service
from backend.app.utils.validator import HallucinationDetector
from backend.app.agents.base import BaseAgent
from backend.app.agents.coordinator import CoordinatorAgent

# Force LLM provider to mock for isolated, hermetic, and fast offline testing
llm_service.provider = "mock"

# Setup database fixtures for testing
@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. UNIT TEST: Database Tools Security and Queries
def test_database_tools_select_only():
    # Attempt a destructive delete statement
    bad_query = "DELETE FROM mom_employment WHERE year = 2020"
    res = execute_sql_query(bad_query)
    assert "Error" in res or "Security" in res

    # Run valid SELECT query
    good_query = "SELECT COUNT(*) as count FROM mom_employment"
    res = execute_sql_query(good_query)
    data = json.loads(res)
    assert isinstance(data, list)
    assert "count" in data[0]

def test_database_schema_retrieval():
    schema = get_database_schema()
    assert "mom_employment" in schema
    assert "singstat_population" in schema
    assert "singstat_cpi" in schema

# 2. UNIT TEST: Mathematical Offloading Tools
def test_math_correlation():
    # Test perfect correlation
    args = json.dumps({
        "array_x": [10, 20, 30, 40],
        "array_y": [100, 200, 300, 400]
    })
    r_val = calculate_correlation(args)
    assert float(r_val) == 1.0

    # Test inverse correlation
    args_inv = json.dumps({
        "array_x": [1, 2, 3],
        "array_y": [3, 2, 1]
    })
    r_inv = calculate_correlation(args_inv)
    assert float(r_inv) == -1.0

def test_math_cagr_growth():
    # Test wage rise CAGR calculation
    args = json.dumps({
        "start_value": 6500,
        "end_value": 8200,
        "periods": 4
    })
    cagr = calculate_growth_rate(args)
    assert "5.98%" in cagr or "5.97%" in cagr or "6.0" in cagr

# 3. CORE REACT AGENT REGEX PARSER TEST
def test_agent_react_parser():
    agent = BaseAgent("TestAgent", "You are testing.")
    
    # Standard ReAct structure
    sample_llm_response = """
    Thought: I need to fetch the database schema.
    Action: get_database_schema
    Action Input: {}
    """
    thought, action, action_input = agent._parse_react_response(sample_llm_response)
    assert "fetch the database schema" in thought
    assert action == "get_database_schema"
    assert "{}" in action_input

    # Conclusion ReAct structure
    conclusion_response = """
    Thought: I have compiled all numbers.
    Final Answer: Median wage rose by 5.9% and has a strong correlation of 0.89 with domestic inflation index.
    """
    thought, action, action_input = agent._parse_react_response(conclusion_response)
    assert "compiled all numbers" in thought
    assert action == "FINAL_ANSWER"
    assert "5.9%" in action_input

# 4. HALLUCINATION DETECTION TEST
def test_hallucination_detector(db_session):
    # Accurate generated brief
    accurate_markdown = """
| Year | Median Monthly Salary (SGD) | Resident Population |
| :--- | :-------------------------: | :-----------------: |
| 2020 | $6,500                      | 5,685,800           |
| 2024 | $8,200                      | 6,050,000           |
"""
    accuracy_report = HallucinationDetector.validate_report(accurate_markdown, db_session)
    assert accuracy_report["status"] == "success"
    assert accuracy_report["mismatches_count"] == 0
    assert accuracy_report["accuracy_score"] == 1.0

    # Hallucinated brief with altered stats
    hallucinated_markdown = """
| Year | Median Monthly Salary (SGD) | Resident Population |
| :--- | :-------------------------: | :-----------------: |
| 2020 | $15,000                     | 5,685,800           |
| 2024 | $8,200                      | 8,000,000           |
"""
    accuracy_report_fail = HallucinationDetector.validate_report(hallucinated_markdown, db_session)
    assert accuracy_report_fail["status"] == "success"
    assert accuracy_report_fail["mismatches_count"] > 0
    assert accuracy_report_fail["accuracy_score"] < 1.0
    
    # Assert specific hallucinated keys are logged
    mismatches = [m["entity"] for m in accuracy_report_fail["mismatches"]]
    assert any("Salary" in m for m in mismatches)
    assert any("Population" in m for m in mismatches)

# 5. ASYNCHRONOUS E2E MULTI-AGENT WORKFLOW INTEGRATION TEST
@pytest.mark.asyncio
async def test_agent_orchestration_workflow():
    # Setup Coordinator
    coordinator = CoordinatorAgent()
    
    # Standard tech query
    query = "Analyze employment trends in the technology sector from 2020-2024 and check wage CAGR."
    res = await coordinator.run_workflow(query)
    
    assert "report" in res
    assert "chart_spec" in res
    assert "# POLICY BRIEF" in res["report"]
    assert "chart_type" in res["chart_spec"]
    assert "data" in res["chart_spec"]
    assert len(res["chart_spec"]["data"]) > 0
