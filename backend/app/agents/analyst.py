import logging
from typing import Callable
from backend.app.agents.base import BaseAgent
from backend.app.tools.math_tools import calculate_correlation, calculate_growth_rate

logger = logging.getLogger("AnalyticsAgent")

SYSTEM_INSTRUCTION = """
You are the Analytics Agent. Your primary role is to run statistical calculations and surface policy-relevant insights from structured datasets.

Responsibilities:
1. Receive clean datasets in JSON format.
2. Use math tools like `calculate_correlation` and `calculate_growth_rate` to extract formal trends and indices. Do NOT perform arithmetic manually — always use the provided tools.
3. Identify core insights, anomalies, and historical developments relevant to the query (e.g., wage growth rates, demographic shifts, economic shocks like the 2023 tech consolidation).
4. In your Final Answer, present:
   - Key statistical findings (correlations, CAGRs, peaks/troughs)
   - Trend narrative with year-by-year commentary
   - Policy implications derived from the data

**Do NOT generate chart JSON or visualization specifications.** Chart rendering is handled separately by a dedicated chart pipeline.

You operate via standard ReAct formatting:
Thought: ...
Action: ...
Action Input: ...
Observation: ...
"""

class AnalyticsAgent(BaseAgent):
    def __init__(self, ws_callback: Callable = None):
        super().__init__(
            name="Analyst",
            system_instruction=SYSTEM_INSTRUCTION,
            ws_callback=ws_callback
        )
        self.register_tool(
            "calculate_correlation",
            calculate_correlation,
            "Computes Pearson's r between x and y. Input: JSON string with 'array_x' and 'array_y'."
        )
        self.register_tool(
            "calculate_growth_rate",
            calculate_growth_rate,
            "Computes CAGR over specified periods. Input: JSON string with 'start_value', 'end_value', and 'periods'."
        )
