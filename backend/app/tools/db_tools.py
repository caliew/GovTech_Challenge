import json
import sqlite3
import re
from backend.app.database import engine

def execute_sql_query(sql_query: str) -> str:
    """
    Executes a read-only SQL query on the local database and returns the result as a JSON string.
    Only SELECT statements are permitted to ensure security and prevent data tampering.
    """
    # 1. Input sanitization - ensure it's a SELECT query only
    sanitized = sql_query.strip().replace("\n", " ")
    if not re.match(r"^\s*SELECT\b", sanitized, re.IGNORECASE):
        return "Error: Security violation. Only SELECT statements are permitted."
    
    # 2. Block any write/destructive commands
    destructive_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "REPLACE"]
    for kw in destructive_keywords:
        if re.search(rf"\b{kw}\b", sanitized, re.IGNORECASE):
            return f"Error: Destructive keyword '{kw}' detected. Action denied."

    # 3. Establish sqlite3 connection using the configured database path
    try:
        # Extract the file path from the DATABASE_URL (strip sqlite:/// prefix)
        from backend.app.config import settings
        db_path = settings.DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        
        # Convert sqlite3.Row elements into serializable dicts
        results = [dict(row) for row in rows]
        conn.close()
        
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Database Error: {str(e)}"

def get_mom_sectors() -> str:
    """Returns the list of unique employment sectors stored in the MOM database."""
    query = "SELECT DISTINCT sector FROM mom_employment"
    return execute_sql_query(query)

def get_database_schema() -> str:
    """Returns a list of tables and column definitions in our schema to help agents plan their SQL queries."""
    schema = """
Available Database Tables and Schema:

1. **mom_employment** (Contains Ministry of Manpower salary and employment records):
   - id: INTEGER (Primary Key)
   - year: INTEGER (2020-2024)
   - sector: TEXT (e.g., 'Technology', 'Financial Services', 'Healthcare', 'Tourism & Hospitality')
   - employment_change: INTEGER (Annual net headcount change, can be negative)
   - unemployment_rate: REAL (Annual unemployment rate in percentage, e.g., 2.4)
   - median_salary: REAL (Median monthly basic salary in SGD, e.g., 8200)

2. **singstat_population** (Contains resident population statistics):
   - id: INTEGER (Primary Key)
   - year: INTEGER (2020-2024)
   - resident_population: INTEGER (Total resident headcount)
   - median_age: REAL (Median age of the population)
   - dependency_ratio: REAL (Ratio of elderly dependents per 100 working residents)

3. **singstat_cpi** (Contains Consumer Price Index for inflation tracking):
   - id: INTEGER (Primary Key)
   - year: INTEGER (2020-2024)
   - month: TEXT (e.g., 'Jan', 'Feb', 'Mar'...)
   - cpi_index: REAL (Inflation index relative to base period)
   - category: TEXT (Category of goods, e.g., 'All Items', 'Food', 'Housing', 'Transport')
"""
    return schema
