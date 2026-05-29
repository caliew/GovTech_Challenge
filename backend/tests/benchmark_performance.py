import time
import asyncio
import json
import statistics
import threading
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal, Base, engine
from backend.app.models import MOMEmployment, SingStatPopulation, SingStatCPI
from backend.app.utils.validator import HallucinationDetector

def format_row(metric, count, avg_time, min_time, max_time, status="PASSED"):
    return f"| {metric:<30} | {count:<10} | {avg_time:<12.4f}s | {min_time:<10.4f}s | {max_time:<10.4f}s | {status:<8} |"

def run_db_query_benchmark(db: Session, iterations=100) -> dict:
    """Benchmark SQL reading times against main tables."""
    latencies = []
    
    for _ in range(iterations):
        start = time.perf_counter()
        # Retrieve all sectors
        _ = db.query(MOMEmployment).filter(MOMEmployment.sector == "Technology").all()
        # Retrieve population
        _ = db.query(SingStatPopulation).all()
        # Retrieve CPI
        _ = db.query(SingStatCPI).filter(SingStatCPI.category == "All Items").all()
        elapsed = time.perf_counter() - start
        latencies.append(elapsed)
        
    return {
        "metric": "DB Table Lookups (Read)",
        "count": iterations,
        "avg": statistics.mean(latencies),
        "min": min(latencies),
        "max": max(latencies)
    }

def run_validator_benchmark(db: Session, iterations=50) -> dict:
    """Benchmark regex markdown parser and SQL factual comparator times."""
    sample_report = """# POLICY BRIEF: Singapore Tech Trends
## Section 1
This is a comprehensive analytical brief of salaries and demographic factors.
## Key Table
| Year | Median Monthly Salary (SGD) | Resident Population |
| :--- | :-------------------------: | :-----------------: |
| 2020 | $6,500                      | 5.69M               |
| 2021 | $7,000                      | 5.45M               |
| 2022 | $7,600                      | 5.64M               |
| 2023 | $7,900                      | 5.92M               |
| 2024 | $8,200                      | 6.05M               |

## General Details
The general tech unemployment rate dropped down to 2.4% indicating full economic recovery.
"""
    latencies = []
    
    for _ in range(iterations):
        start = time.perf_counter()
        _ = HallucinationDetector.validate_report(sample_report, db)
        elapsed = time.perf_counter() - start
        latencies.append(elapsed)
        
    return {
        "metric": "Hallucination Validation",
        "count": iterations,
        "avg": statistics.mean(latencies),
        "min": min(latencies),
        "max": max(latencies)
    }

def run_concurrent_load_simulation(db_class, num_threads=10, iterations_per_thread=20) -> dict:
    """Simulates parallel client connections querying SQLite concurrently."""
    latencies = []
    lock = threading.Lock()
    
    def thread_worker():
        db = db_class()
        thread_latencies = []
        for _ in range(iterations_per_thread):
            start = time.perf_counter()
            # Perform read-heavy operations
            _ = db.query(MOMEmployment).all()
            _ = db.query(SingStatPopulation).all()
            elapsed = time.perf_counter() - start
            thread_latencies.append(elapsed)
        db.close()
        
        with lock:
            latencies.extend(thread_latencies)
            
    threads = []
    start_sim = time.perf_counter()
    for _ in range(num_threads):
        t = threading.Thread(target=thread_worker)
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    total_duration = time.perf_counter() - start_sim
    
    return {
        "metric": f"Concurrent Load ({num_threads} Clients)",
        "count": len(latencies),
        "avg": statistics.mean(latencies),
        "min": min(latencies),
        "max": max(latencies),
        "total_elapsed": total_duration
    }

def main():
    print("=" * 95)
    print("      GOVTECH POLICY PLATFORM: PERFORMANCE & LOAD TESTING BENCHMARK HARNESS")
    print("=" * 95)
    print("Initializing SQLite database connection and loading seed factors...")
    
    db = SessionLocal()
    
    # Run Seeding if database is not ready
    from backend.app.seed_data import seed_database
    seed_database(db)
    
    print("\nExecuting metrics benchmarks...")
    
    db_query_res = run_db_query_benchmark(db, iterations=100)
    validator_res = run_validator_benchmark(db, iterations=50)
    load_res = run_concurrent_load_simulation(SessionLocal, num_threads=15, iterations_per_thread=25)
    
    db.close()
    
    # 1. Print structured ASCII results table
    divider = "-" * 95
    print("\nBenchmark Execution Complete!\n")
    print(divider)
    print(f"| {'Metric / Benchmark Domain':<30} | {'Iterations':<10} | {'Avg Latency':<12} | {'Min Latency':<11} | {'Max Latency':<11} | {'Status':<8} |")
    print(divider)
    print(format_row(db_query_res["metric"], db_query_res["count"], db_query_res["avg"], db_query_res["min"], db_query_res["max"]))
    print(format_row(validator_res["metric"], validator_res["count"], validator_res["avg"], validator_res["min"], validator_res["max"]))
    print(format_row(load_res["metric"], load_res["count"], load_res["avg"], load_res["min"], load_res["max"]))
    print(divider)
    print(f"Total concurrent simulation runtime: {load_res['total_elapsed']:.4f} seconds.")
    print("=" * 95)
    
    # 2. Write findings to JSON artifact
    results_json = {
        "timestamp": time.time(),
        "database_read_benchmark": db_query_res,
        "hallucination_validator_benchmark": validator_res,
        "concurrency_simulation": load_res
    }
    
    output_path = "backend/tests/benchmark_results.json"
    with open(output_path, "w") as f:
        json.dump(results_json, f, indent=2)
    print(f"Detailed performance benchmark log written to: [benchmark_results.json]({output_path})")

if __name__ == "__main__":
    main()
