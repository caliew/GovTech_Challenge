import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.database import get_db, Base
from backend.app.utils.llm import llm_service
import backend.app.main as main_module
from backend.app.models import AnalysisRequest, AgentLog, AnalysisResult

# Force LLM provider to mock for isolated, hermetic, and fast offline testing
llm_service.provider = "mock"

# 1. Setup isolated in-memory database for API testing with StaticPool
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Create schema in the in-memory DB
Base.metadata.create_all(bind=test_engine)

# 2. Dependency Overrides
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Patch direct SessionLocal calls in main.py to use our in-memory DB session
main_module.SessionLocal = TestingSessionLocal

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_database():
    """Clear all records before each test to maintain test isolation."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    # Seed minimal mock tables needed for testing in memory
    from backend.app.seed_data import seed_database
    db = TestingSessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

# 3. Test REST Endpoints

def test_api_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data

def test_api_list_empty_requests():
    # Database is empty of analysis requests at first
    response = client.get("/api/requests")
    assert response.status_code == 200
    assert response.json() == []

def test_api_get_request_details_404():
    response = client.get("/api/requests/nonexistent-uuid")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_api_create_and_fetch_request():
    # Insert a dummy AnalysisRequest directly
    db = TestingSessionLocal()
    req = AnalysisRequest(id="test-req-123", user_query="Analyze tech inflation trends", status="completed")
    log = AgentLog(request_id="test-req-123", agent_name="Coordinator", step_type="thought", content="Analyzing sector data...")
    res = AnalysisResult(request_id="test-req-123", final_report="# Success report", chart_data='{"chart_type": "bar"}')
    db.add(req)
    db.add(log)
    db.add(res)
    db.commit()
    db.close()

    # Verify listing displays it
    list_resp = client.get("/api/requests")
    assert list_resp.status_code == 200
    req_list = list_resp.json()
    assert len(req_list) == 1
    assert req_list[0]["id"] == "test-req-123"
    assert req_list[0]["query"] == "Analyze tech inflation trends"

    # Verify detail retrieval returns correct logs and results
    detail_resp = client.get("/api/requests/test-req-123")
    assert detail_resp.status_code == 200
    details = detail_resp.json()
    assert details["query"] == "Analyze tech inflation trends"
    assert len(details["logs"]) == 1
    assert details["logs"][0]["agent"] == "Coordinator"
    assert details["logs"][0]["content"] == "Analyzing sector data..."
    assert details["result"]["report"] == "# Success report"
    assert details["result"]["chart_spec"]["chart_type"] == "bar"

# 4. Test WebSocket Endpoint

def test_api_ws_analysis_workflow():
    # Connect to websocket endpoint
    with client.websocket_connect("/api/ws/analysis") as websocket:
        # Send initial query payload
        query_payload = {"query": "Analyze employment trends in the technology sector from 2020-2024"}
        websocket.send_text(json.dumps(query_payload))

        # Receive streaming steps
        messages = []
        try:
            # We expect standard agent events: planning, extractions, analyst summaries, and finally completion.
            # We'll read up to 100 messages or until a "completed" message is received.
            for _ in range(100):
                msg_str = websocket.receive_text()
                msg = json.loads(msg_str)
                messages.append(msg)
                if msg.get("type") == "completed":
                    break
        except Exception as e:
            pytest.fail(f"WebSocket communication failed: {e}")

        # Assertions
        assert len(messages) > 0
        
        # Verify coordination logs are present
        coordinator_logs = [m for m in messages if m.get("agent") == "Coordinator"]
        assert len(coordinator_logs) > 0
        
        # Verify status transitions are logged
        status_logs = [m for m in messages if m.get("type") == "status"]
        assert len(status_logs) > 0
        
        # Verify a final completed signal with report and chart spec is returned
        final_msg = messages[-1]
        assert final_msg["type"] == "completed"
        assert "report" in final_msg
        assert "chart_spec" in final_msg
        assert "# POLICY BRIEF" in final_msg["report"]
        assert "chart_type" in final_msg["chart_spec"]
