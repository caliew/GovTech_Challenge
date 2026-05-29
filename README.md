# GovTech Agentic Policy Analytics Platform

An intelligent, multi-agent full-stack analytics platform built to orchestrate data extraction, run statistical computations, and compile verified, publication-grade policy briefs on Singapore's socio-economic and demographic datasets.

---

## 🌟 Key Features

* **Asynchronous Multi-Agent Architecture**: Built around a custom event-driven ReAct (Reasoning, Action, Observation) loop, featuring a central **Data Coordinator**, a sandboxed **Data Extractor**, and a mathematical **Analytics Agent** cooperating dynamically.
* **Deterministic Hallucination Detection**: Features a validation engine that cross-references text and generated tables in policy reports back to the SQL database using a 2% rounding tolerance and logs factual mismatches programmatically.
* **Real-time Log Streaming**: Visualizes the internal thought processes, tool executions, and findings of the multi-agent system in a real-time terminal window via WebSockets.
* **Interactive Data Visualizations**: Renders dynamic, responsive charts built in Recharts using JSON coordinate configurations constructed by the Analytics Agent.
* **Multi-Cloud LLM Resilience Wrapper**: Seamlessly falls back from `OpenAI GPT-4o-mini` to `GCP Gemini 1.5 Flash`, with support for an offline heuristics engine when API keys are not provided.

---

## 📂 Repository Structure

* [CHALLENGE.md](file:///c:/WebPortal/GovTech_Challenge/CHALLENGE.md): The original challenge description and requirements.
* [ARCHITECTURE.md](file:///c:/WebPortal/GovTech_Challenge/ARCHITECTURE.md): Technical system design, database schemas, agent monologues, and flow charts.
* [TESTING.md](file:///c:/WebPortal/GovTech_Challenge/TESTING.md): Verification strategy, hallucination validation math, and load benchmarking.
* [DATA_SOURCES.md](file:///c:/WebPortal/GovTech_Challenge/DATA_SOURCES.md): Government dataset outlines and seeding instructions.
* [INNOVATION_ASSESSMENT.md](file:///c:/WebPortal/GovTech_Challenge/INNOVATION_ASSESSMENT.md): Detailed responses to structural questions, trade-offs, and scaling plans.
* [backend/](file:///c:/WebPortal/GovTech_Challenge/backend): FastAPI async REST and WebSocket servers, agents, tools, and DB models.
* [frontend/](file:///c:/WebPortal/GovTech_Challenge/frontend): React TS application serving the user console dashboard.

---

## 🚀 Setup & Launch Instructions

### Prerequisites
* **Python 3.11+**
* **Node.js 20+**
* **Docker & Docker Compose** (Optional, for containerized run)

### Option A: Local Host Launch (Natively)

#### 1. Setup Backend
1. Navigate to the project root:
   ```bash
   cd c:/WebPortal/GovTech_Challenge
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv backend/venv
   .\backend\venv\Scripts\Activate.ps1
   ```
3. Install Python dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
4. Configure environment variables (copy `.env.example` to `.env` and fill in API keys if available):
   ```bash
   copy .env.example .env
   ```
5. Initialize and seed the SQLite database:
   ```bash
   python -c "from backend.app.database import init_db; init_db()"
   ```
6. Start the FastAPI development server:
   ```bash
   uvicorn backend.app.main:app --reload
   ```
   *(Running at `http://localhost:8000`)*

#### 2. Setup Frontend
1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd c:/WebPortal/GovTech_Challenge/frontend
   ```
2. Install Node packages:
   ```bash
   npm install
   ```
3. Start the Vite React development server:
   ```bash
   npm run dev
   ```
   *(Accessible at `http://localhost:5173`)*

---

### Option B: Docker Containers (Recommended)

To build and spin up the complete full-stack environment instantly inside Docker containers:
1. Navigate to the project root:
   ```bash
   cd c:/WebPortal/GovTech_Challenge
   ```
2. Run docker compose build and run:
   ```bash
   docker-compose up --build
   ```
3. Open `http://localhost:80` (production Nginx proxying request pipelines) or `http://localhost:5173` (development frontend mapping) in your browser.

---

## 🧪 Running the Test Suites

### Backend Unit Tests & Coverage
Our backend includes `pytest-cov` verification which generates coverage HTML and JSON reports, enforcing a strict minimum threshold of `70%`.
* **Run natively (with coverage)**:
  ```powershell
  .\backend\venv\Scripts\pytest
  ```
* **Run inside Docker**:
  ```bash
  docker-compose exec backend pytest
  ```

### Frontend Unit Tests & Coverage
Our frontend uses `Vitest` and `JSDOM` to verify UI responsiveness, settings manipulation, and WebSocket pipelines.
* **Run natively (with coverage)**:
  ```bash
  cd frontend
  npm run coverage
  ```

---

## 📊 Sample Queries to Try

You can type these queries into the research input box or click their corresponding quick-start template buttons on the dashboard:
1. **Employment & Inflation Brief**:
   > *"Analyze employment trends in the technology sector from 2020-2024 and compare with inflation."*
2. **Demographics & Population Balance**:
   > *"Evaluate resident population median age trends and demographic dependency ratios (2020-2024)."*
3. **Tourism Sector Recovery**:
   > *"Investigate tourism sector recovery post-pandemic and check wage growth indices compared to CPI."*

---

## 🛠️ Technology Justification

| Layer | Choice | Justification |
|---|---|---|
| **Backend Framework** | **FastAPI** | Extremely fast async processing capabilities. Ideal for streaming WebSocket monologue frames and concurrent request handling. |
| **Database** | **SQLite + SQLAlchemy** | Highly responsive local, file-based relational database. Avoids heavy network connections during live demos while maintaining SQL relational compliance. |
| **Agentic Framework** | **Custom ReAct Loop** | Avoids heavy agent frameworks (e.g. CrewAI, LangGraph) which trigger dependency compile issues on Windows. ReAct loop is custom-built with pure Python generators to achieve direct frame-by-frame streaming. |
| **Math Execution** | **Python Offloader** | Keeps agents from attempting arithmetic inside LLM prompt logs. Programmatic python scripts compute CAGR and Pearson correlation to guarantee 100% calculation accuracy. |
| **Frontend Framework** | **React + TS + Vite** | Instant module updates, strong type safety, and fast compile speeds. Supports dynamic rendering of WebSocket streams. |
| **Charts** | **Recharts** | Interactive, svg-responsive canvas library that seamlessly binds to JSON data configurations. |
| **UI Aesthetics** | **Glassmorphism Tailwind** | Premium neon-tinted dark-mode styling giving the dashboard an intuitive, futuristic console feeling. |
