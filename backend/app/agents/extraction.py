import logging
from typing import Callable
from backend.app.agents.base import BaseAgent
from backend.app.tools.db_tools import execute_sql_query, get_database_schema
from backend.app.tools.api_tools import fetch_regional_inflation_api, fetch_global_tech_index_api

logger = logging.getLogger("ExtractionAgent")

SYSTEM_INSTRUCTION = """
You are the Data Extraction Agent. Your primary role is to extract quantitative datasets from local database schemas and external mock APIs in response to a policy query.

Responsibilities:
1. Always explore the database schema first using `get_database_schema` before executing any SQL queries.
2. Build precise, clean SELECT statements to gather relevant columns. Do NOT perform complex calculations or aggregations—simply extract, clean, and format.
3. Clean and validate the extracted data:
   - Verify that columns contain the expected data types.
   - Detect missing cells (nulls, empties) and handle them (fill with averages, zeroes, or drop).
   - Format and normalize column headers (e.g., standard lowercase with underscores).
4. Package the resulting data into a clean, serializable JSON format.
5. In your Final Answer, present a detailed data quality validation report alongside the JSON payload.

You operate via standard ReAct formatting:
Thought: ...
Action: ...
Action Input: ...
Observation: ...
"""

class ExtractionAgent(BaseAgent):
    def __init__(self, ws_callback: Callable = None):
        super().__init__(
            name="Extractor",
            system_instruction=SYSTEM_INSTRUCTION,
            ws_callback=ws_callback
        )
        # Register DB Tools
        self.register_tool(
            "get_database_schema", 
            lambda x: get_database_schema(), 
            "Retrieves table definitions and column details for our SQLite database."
        )
        self.register_tool(
            "execute_sql_query", 
            execute_sql_query, 
            "Executes a read-only SELECT SQL query on the local database. Input must be a valid SELECT statement."
        )
        
        # Register Mock API Tools
        self.register_tool(
            "fetch_regional_inflation_api", 
            fetch_regional_inflation_api, 
            "Fetches Southeast Asia regional inflation data. Input is a year string (e.g., '2022')."
        )
        self.register_tool(
            "fetch_global_tech_index_api", 
            fetch_global_tech_index_api, 
            "Fetches global technology talent demand indices. Input is a year string (e.g., '2024')."
        )
