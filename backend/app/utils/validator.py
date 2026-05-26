import re
import json
import logging
from sqlalchemy.orm import Session
from backend.app.models import MOMEmployment, SingStatPopulation, SingStatCPI

logger = logging.getLogger("FactualValidator")

class HallucinationDetector:
    @staticmethod
    def extract_numbers_from_text(text: str) -> list:
        """Helper to find all integer or decimal numbers in a string block."""
        return [float(n) for n in re.findall(r"\b\d+(?:\.\d+)?\b", text)]

    @staticmethod
    def parse_markdown_tables(report_markdown: str) -> list:
        """
        Parses all markdown tables in the report.
        Returns a list of dict rows representing cell values.
        """
        tables = []
        # Find markdown table blocks
        table_blocks = re.findall(r"((?:\|.*\|(?:\r?\n|$))+)", report_markdown)
        
        for block in table_blocks:
            lines = [line.strip() for line in block.split("\n") if line.strip()]
            if len(lines) < 3:
                continue  # Need at least header, divider, and 1 row
                
            # Parse headers
            headers = [h.strip() for h in lines[0].split("|")[1:-1]]
            
            rows = []
            for line in lines[2:]:
                if "---" in line or ":---" in line:
                    continue
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if len(cells) == len(headers):
                    rows.append(dict(zip(headers, cells)))
            tables.append(rows)
            
        return tables

    @staticmethod
    def validate_report(report_markdown: str, db: Session) -> dict:
        """
        Extracts numerical values from the markdown report (tables & text) 
        and compares them against factual SQLite entries.
        """
        logger.info("Running automated hallucination detection and data accuracy checks...")
        
        mismatches = []
        validated_facts = []
        data_quality_warnings = []
        
        # 1. Parse markdown tables
        tables = HallucinationDetector.parse_markdown_tables(report_markdown)
        
        # Pull factual data from SQLite for verification
        try:
            db_tech_recs = db.query(MOMEmployment).filter(MOMEmployment.sector == "Technology").all()
            db_population_recs = db.query(SingStatPopulation).all()
            
            tech_facts = {r.year: r for r in db_tech_recs}
            pop_facts = {r.year: r for r in db_population_recs}
        except Exception as e:
            logger.error(f"Failed to query verification facts from SQLite: {e}")
            return {"status": "error", "message": f"Database verification failed: {e}"}

        # 2. Verify Table Columns if present
        for table in tables:
            for row in table:
                # Find the year column
                year_cell = None
                for key in row.keys():
                    if "year" in key.lower():
                        year_cell = row[key]
                        break
                        
                if not year_cell:
                    continue
                    
                # Extract year integer
                try:
                    year = int(re.search(r"\b(202\d)\b", year_cell).group(1))
                except Exception:
                    continue

                # A. Verify Tech Salaries
                for key, val in row.items():
                    if "salary" in key.lower() or "sgd" in key.lower():
                        raw_val = val.replace(",", "")
                        nums = HallucinationDetector.extract_numbers_from_text(raw_val)
                        if nums and year in tech_facts:
                            report_val = nums[0]
                            fact_val = tech_facts[year].median_salary
                            
                            # Standardize check (e.g. handle monthly vs annual scale if any)
                            if abs(report_val - fact_val) > 0.01:
                                mismatches.append({
                                    "entity": f"Technology Sector Salary ({year})",
                                    "reported_value": val,
                                    "factual_value": f"${fact_val:,.2f}",
                                    "source": "MOM Table Schema Check"
                                })
                            else:
                                validated_facts.append({
                                    "entity": f"Technology Sector Salary ({year})",
                                    "value": val
                                })

                    # B. Verify Resident Population
                    if "population" in key.lower() or "resident" in key.lower():
                        # Standardize (could be written as e.g. 5,685,800 or 5.69M)
                        raw_val = val.replace(",", "")
                        nums = HallucinationDetector.extract_numbers_from_text(raw_val)
                        if nums and year in pop_facts:
                            report_val = nums[0]
                            fact_val = pop_facts[year].resident_population
                            
                            # Handle millions scaling in report (e.g., 5.68M -> 5680000)
                            if "m" in val.lower() and report_val < 100:
                                report_val = report_val * 1_000_000

                            # Allow 2% tolerance for rounded formats (e.g., 5.69M vs 5685800)
                            deviation_pct = abs(report_val - fact_val) / fact_val
                            if deviation_pct > 0.02:
                                mismatches.append({
                                    "entity": f"Singapore Resident Population ({year})",
                                    "reported_value": val,
                                    "factual_value": f"{fact_val:,.0f}",
                                    "source": "SingStat Population Check"
                                })
                            else:
                                validated_facts.append({
                                    "entity": f"Singapore Resident Population ({year})",
                                    "value": val
                                })

        # 3. Scan general text for dangerous wild deviations (unsupported years/claims)
        # Scan for extremely large figures that claim to represent unemployment
        unemployment_deviations = re.findall(r"\bunemployment(?:.*?)(\d+(?:\.\d+)?)\s*%", report_markdown, re.IGNORECASE)
        for rate_str in unemployment_deviations:
            rate = float(rate_str)
            if rate > 12.0:  # Singapore's unemployment rate has never reached 12% in 2020-2024
                mismatches.append({
                    "entity": "Anomaly detection: Generic Unemployment Rate",
                    "reported_value": f"{rate}%",
                    "factual_value": "< 4.5%",
                    "source": "Heuristic Out-Of-Bounds check"
                })

        accuracy_score = 1.0
        total_checks = len(validated_facts) + len(mismatches)
        if total_checks > 0:
            accuracy_score = len(validated_facts) / total_checks

        return {
            "status": "success",
            "accuracy_score": round(accuracy_score, 4),
            "validated_facts_count": len(validated_facts),
            "mismatches_count": len(mismatches),
            "validated_facts": validated_facts,
            "mismatches": mismatches,
            "quality_warnings": data_quality_warnings
        }
