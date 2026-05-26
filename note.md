# GovTech Agentic Policy Data Analytics Platform: Setup & Execution Options

This document outlines the three setup topologies available for running, developing, and presenting the application.

---

## 🚀 Option A: Pure Native Setup (Local Host)

Runs both the Frontend React client and the Backend FastAPI server directly on the Windows host machine.

### Prerequisites

* **Python**: Stable version installed (Python 3.11 or 3.12). *Do not use Python 3.14 (pre-release) as it requires a Rust/C++ compilation toolchain for dependencies.*
* **Node.js**: Installed (for npm/npx).

### Steps to Run

1. **Launch the Backend**:
   Open a terminal in the `./backend` folder:

   ```powershell
   # 1. Create a Python virtual environment
   python -m venv venv

   # 2. Activate the virtual environment
   .\venv\Scripts\Activate.ps1

   # 3. Install project dependencies
   pip install -r requirements.txt

   # 4. Start the FastAPI backend with hot-reload
   uvicorn app.main:app --reload

   # 5. How to Fix Option A (Native Local Setup)
    Run uvicorn from the project root: Navigate back to the project root and start uvicorn using the virtual environment's path:
    cd ..
    .\backend\venv\Scripts\uvicorn backend.app.main:app --reload
   ```

   *The backend will serve at: `http://localhost:8000`*

2. **Launch the Frontend**:
   Open a separate terminal in the `./frontend` folder:

   ```powershell
   # Start the local Vite development server
   npx vite
   ```

   *The frontend UI will serve at: `http://localhost:5173` (with instant HMR).*

---

## 🐳 Option B: Pure Docker Setup (Zero Local Install)

**Best for Interiewers / Evaluators.** Runs both backend and frontend inside containers. No need to install Python, Node.js, or local libraries on the system.

### Prerequisites

* **Docker Desktop**: Installed and running on the host system.

### Steps to Run

1. From the project root (`./`), run:

   ```bash
   docker-compose up --build
   ```

2. This compiles the production assets, starts the SQLite database, and hosts:
   * **Frontend UI Dashboard** at `http://localhost:5173` (Served via Nginx container).
   * **Backend REST/WS API Server** at `http://localhost:8000` (Served via Python 3.11 container).

---

## 🔀 Option C: Hybrid Dev Setup (Docker Backend + Native Frontend)

**Recommended for active development.** Packages the Python backend in a stable Docker container with live-mounted volume folders so you get instant reload on `.py` saves without installing Python or libraries on your host. Runs the React frontend natively on Vite for sub-second hot-module replacement.

### Prerequisites

* **Docker Desktop** (active).
* **Node.js** (for native frontend).

### Steps to Run

1. **Backend (Docker Container)**:
   Launch the dev-configured container from the project root:

   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
   ```

   *This live-mounts `./backend` and runs uvicorn inside Docker with `--reload` enabled. Any saved `.py` file changes sync and hot-restart inside the container.*

2. **Frontend (Native Host)**:
   Run natively inside `./frontend` for the fastest UI feedback loops:

   ```bash
   npx vite
   ```
