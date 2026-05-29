import os
import json
import logging
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from backend.app.config import settings
from backend.app.database import engine, Base, get_db, SessionLocal
from backend.app.models import AnalysisRequest, AgentLog, AnalysisResult
from backend.app.seed_data import seed_database
from backend.app.agents.coordinator import CoordinatorAgent

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GovTechAPI")

# Initialize SQLite database schema
Base.metadata.create_all(bind=engine)

# Auto-seed database if empty on startup
db = SessionLocal()
try:
    seed_database(db)
finally:
    db.close()

app = FastAPI(
    title="GovTech Agentic Policy Data Analytics Platform",
    description="REST API and WebSocket server for multi-agent policy research automation.",
    version="1.0.0"
)

# Configure CORS for Frontend connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Enable access from any host during dev/demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    """Simple API health check endpoint."""
    return {
        "status": "healthy",
        "database": "connected",
        "environment": settings.ENVIRONMENT,
        "llm_provider": settings.LLM_PROVIDER
    }

@app.get("/api/requests")
def list_analysis_requests(db: Session = Depends(get_db)):
    """Retrieves previous analysis requests ordered by date."""
    requests = db.query(AnalysisRequest).order_by(AnalysisRequest.created_at.desc()).all()
    return [
        {
            "id": req.id,
            "query": req.user_query,
            "status": req.status,
            "created_at": req.created_at.isoformat()
        } for req in requests
    ]

@app.get("/api/requests/{request_id}")
def get_analysis_details(request_id: str, db: Session = Depends(get_db)):
    """Retrieves full details of a specific request, including agent logs and generated brief."""
    req = db.query(AnalysisRequest).filter(AnalysisRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Analysis request not found.")
        
    logs = db.query(AgentLog).filter(AgentLog.request_id == request_id).order_by(AgentLog.id.asc()).all()
    result = db.query(AnalysisResult).filter(AnalysisResult.request_id == request_id).first()

    return {
        "id": req.id,
        "query": req.user_query,
        "status": req.status,
        "created_at": req.created_at.isoformat(),
        "logs": [
            {
                "agent": log.agent_name,
                "type": log.step_type,
                "content": log.content,
                "created_at": log.created_at.isoformat()
            } for log in logs
        ],
        "result": {
            "report": result.final_report if result else None,
            "chart_spec": json.loads(result.chart_data) if result and result.chart_data else None
        } if result else None
    }

@app.websocket("/api/ws/analysis")
async def websocket_analysis_endpoint(websocket: WebSocket):
    """
    Handles real-time analysis requests via WebSockets.
    Pushes intermediate agent monologues, tool calls, observations, and streams the final report.
    """
    await websocket.accept()
    logger.info("🟢 WEBSOCKET CONNECTION ESTABLISHED 🟢")

    try:
        # 1. Listen for user query
        data = await websocket.receive_text()
        payload = json.loads(data)
        query = payload.get("query")
        
        if not query:
            await websocket.send_text(json.dumps({"type": "error", "content": "Missing query parameter."}))
            await websocket.close()
            return

        # 2. Register Request in Database
        db = SessionLocal()
        req = AnalysisRequest(user_query=query, status="processing")
        db.add(req)
        db.commit()
        db.refresh(req)
        request_id = req.id
        db.close()

        # 🔴🟢🟠🟡🟣
        logger.info(f"🟢 STARTED ANALYSIS TASK '{request_id}'")
        logger.info(f"🟢 QUERY : '{query}'")

        # 3. Define Callback to stream agent thoughts to both Database & WebSocket
        async def ws_callback(step: dict):
            # step keys: agent, type (thought/action/observation/status/result), content
            step["request_id"] = request_id
            
            # Send live over WebSocket
            await websocket.send_text(json.dumps(step))
            
            # Save to SQLite asynchronously (in threadsafe session)
            db_session = SessionLocal()
            try:
                log_entry = AgentLog(
                    request_id=request_id,
                    agent_name=step["agent"],
                    step_type=step["type"],
                    content=step["content"]
                )
                db_session.add(log_entry)
                db_session.commit()
            except Exception as e:
                logger.error(f"Failed to save agent log to DB: {e}")
            finally:
                db_session.close()

        # 4. Instantiate and Run Multi-Agent Orchestrator
        logger.info(f"🟢 INSTANTIATE AND RUN MULTI-AGENT ORCHESTRATOR 🟢")
        coordinator = CoordinatorAgent(ws_callback=ws_callback)
        
        try:
            workflow_result = await coordinator.run_workflow(query)
            
            # 5. Save Final Output in DB
            db_session = SessionLocal()
            req_db = db_session.query(AnalysisRequest).filter(AnalysisRequest.id == request_id).first()
            req_db.status = "completed"
            
            result_db = AnalysisResult(
                request_id=request_id,
                final_report=workflow_result["report"],
                chart_data=json.dumps(workflow_result["chart_spec"])
            )
            db_session.add(result_db)
            db_session.commit()
            db_session.close()

            # Pushes final signal with completed assets
            await websocket.send_text(json.dumps({
                "agent": "System",
                "type": "completed",
                "request_id": request_id,
                "report": workflow_result["report"],
                "chart_spec": workflow_result["chart_spec"]
            }))
            
            logger.info(f"🟢 SUCCESSFULY COMPLETED ANALYSIS REQUEST '{request_id}' 🟢")

        except Exception as err:
            logger.error(f"Error during agentic workflow: {err}")
            
            db_session = SessionLocal()
            req_db = db_session.query(AnalysisRequest).filter(AnalysisRequest.id == request_id).first()
            if req_db:
                req_db.status = "failed"
                db_session.commit()
            db_session.close()

            await websocket.send_text(json.dumps({
                "agent": "System",
                "type": "error",
                "content": f"An unexpected error occurred during analysis: {str(err)}"
            }))

    except WebSocketDisconnect:
        logger.info("🟢 WEBSOCKET DISCONNECTED BY CLIENT 🟢")
    except Exception as e:
        logger.error(f"🟢 WEBSOCKET ERROR : {e} 🟢")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
