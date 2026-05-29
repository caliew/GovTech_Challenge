# TESTING.md: Quality Assurance & Hallucination Detection

A detailed breakdown of the comprehensive test suite, data validation patterns, and factual accuracy checks implemented on the platform.

---

## 1. Testing Strategy and Methodology

We established a multi-tiered test suite targeting separate layers of the platform using **pytest** (configured with `pytest-asyncio` for asynchronous agent loops):

```
                        +-----------------------------------------+
                        |          Automated CI/CD Test           |
                        |      (GitHub Actions Workflow Run)      |
                        +--------------------+--------------------+
                                             |
                                             v
                        +-----------------------------------------+
                        |        Hallucination Detection          |
                        |  (Determinisitic Database Comparators)  |
                        +--------------------+--------------------+
                                             |
                                             v
                        +--------------------+--------------------+
                        |            Integration Tests            |
                        |     (Async Multi-Agent Workflows)       |
                        +--------------------+--------------------+
                                             |
                                             v
                        +--------------------+--------------------+
                        |               Unit Tests                |
                        |      (SQL Tools, Math, LLM, Regex)      |
                        +-----------------------------------------+
```

### Core Test Suites (`backend/tests/test_agents.py`)
1. **Database Tools Unit Tests:**
   - Verifies sandboxed security checks in `execute_sql_query` to block any destructive SQL operations (`DELETE`, `UPDATE`, `DROP`).
   - Asserts correct retrieval of column definitions in `get_database_schema`.
2. **Mathematical Offloading Unit Tests:**
   - Verifies perfect positive and inverse Pearson correlation calculations (`calculate_correlation`) against known datasets.
   - Asserts CAGR formulas (`calculate_growth_rate`) are programmatically correct.
3. **Regex Prompt Parser Unit Tests:**
   - Asserts that standard ReAct monologues (containing `Thought:`, `Action:`, and `Action Input:`) are extracted cleanly into actionable payloads.
   - Verifies that conclusory agent outputs correctly transition to `FINAL_ANSWER` status.
4. **Automated Hallucination Detection Tests:**
   - Asserts that accurate markdown policy briefs evaluate to a perfect factual accuracy score (`1.0`).
   - Asserts that a modified markdown brief (containing fabricated tech salaries or population statistics) is successfully flagged, resulting in specific mismatch records and a lower accuracy score.
5. **End-to-End Async Orchestration Tests:**
   - Runs a full asynchronous simulation of the Data Coordinator coordinating Extractor and Analyst agents, asserting correct final briefs and chart formats.

---

## 2. Programmatic Hallucination Detection

To solve the critical challenge of AI factual hallucinations, we engineered a deterministic validator layer (`validator.py`) which acts as a mathematical gatekeeper:

```
    [Markdown Report] ---> [Markdown Table Parser] ---> [Row Values Extraction] 
                                                                |
    [Ground-Truth SQL] <--- [Factual DB Comparator] <-----------+
            |
            v
    [Accuracy Score & Mismatches Log]
```

### Detection Workflow
1. **Table Extraction:** The validator parses markdown text using regular expressions to locate all markdown table syntax, parsing columns and rows into memory.
2. **Ground-Truth Retrieval:** Based on the identified rows, the validator extracts the primary key parameters (e.g., Year and Sector) and queries the local SQLite database for the ground-truth facts.
3. **Cell Comparators:** 
   - **Wage/Salary columns:** Compares numeric entries directly.
   - **Demographic Population columns:** Normalizes commas and notation (e.g. `5.69M` vs `5,685,800`), applies a 2% rounding tolerance, and flags any wild deviations.
4. **Out-of-Bounds Heuristics:** Scans raw paragraphs for dangerous claims (such as claiming Singapore sector unemployment rates reached `15%` or higher during 2020-2024), logging anomalies as out-of-bounds failures.
5. **Quality Score:** Calculates the final score:
   $$\text{Factual Accuracy Score} = \frac{\text{Validated Facts}}{\text{Validated Facts} + \text{Mismatches}}$$
   Reports with a score under `1.0` flag factual warnings on the console dashboard.

---

## 3. How to Run Automated Tests

### Option A: Run Tests Natively (Local Host Environment)
Ensure Python dependencies inside `backend/requirements.txt` are fully installed.
Execute from the project workspace root:
```bash
python -m pytest backend/tests/
```
This runs the entire test suite, including:
1. `test_agents.py`: Base ReAct parser, SQL sandboxing tools, mathematical offloading formulas, and async orchestration integrations.
2. `test_api.py`: FastAPI health checks, historic request listings, detailed single-request fetches, and real-time analytical WebSockets (mocking expensive LLM API queries with mock events).
3. `test_data_quality.py`: Resiliency evaluations for malformed markdown tables, numerical parsing, scaling modifiers (e.g., `M`), the 2% rounding tolerance limits, and out-of-bounds anomaly flagging.

### Option B: Run Tests inside Docker Containers (Recommended)
With the Docker containers active, execute from the workspace root:
```bash
docker-compose exec backend pytest backend/tests/
```
You will receive a complete, color-coded execution report demonstrating test coverage!

---

## 4. Performance & Load Benchmarking

To fulfill the requirements of high concurrency and low latency in policy environments, we engineered a benchmarking harness at `backend/tests/benchmark_performance.py`.

### Benchmark Coverage
* **DB Read Latency:** Performs 100 read cycles against the MOM employment, SingStat population, and CPI index tables, reporting average query speeds.
* **Validator Throughput:** Parses and performs factual comparisons against standard and edge-case reports 50 times to test regular expression and comparison speed.
* **Concurrent Load Simulator:** Simulates 15 active client connections running 25 database analytical reads each in parallel (375 total executions) to evaluate thread safety and SQLite thread lock speeds.

### Running the Performance Benchmark
Execute natively from the project workspace root:
```bash
python backend/tests/benchmark_performance.py
```
Or execute inside the active Docker backend container:
```bash
docker-compose exec backend python backend/tests/benchmark_performance.py
```

### Verification & Outcome
Upon completion, the harness:
1. Prints a beautifully formatted ASCII table of results to stdout showing the **Iterations**, **Average Latency**, **Minimum Latency**, **Maximum Latency**, and **Status**.
2. Writes the full JSON logs of the run to `backend/tests/benchmark_results.json` for validation and programmatic CI/CD quality gates.

