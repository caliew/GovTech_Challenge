import logging
from typing import Callable
from backend.app.agents.base import BaseAgent
from backend.app.tools.math_tools import calculate_correlation, calculate_growth_rate

logger = logging.getLogger("AnalyticsAgent")

SYSTEM_INSTRUCTION = """
You are the Analytics Agent. Your primary role is to run statistical calculations, detect policy-relevant trends, and generate data visualization specifications.

Responsibilities:
1. Receive clean datasets in JSON format.
2. Use math tools like `calculate_correlation` and `calculate_growth_rate` to extract formal trends and indices (avoid manual LLM math arithmetic).
3. Identify core insights, anomalies, or historical developments (e.g., wage growth, demographic shifts, economic shocks like the 2023 consolidation).
4. Generate a declarative **JSON visualization specification** representing the best chart format to communicate findings. The JSON specification must look like this:
   {
     "chart_type": "Line" or "Bar" or "Area" or "Composed",
     "title": "Chart Title",
     "xAxis": "column_for_x_axis",
     "series": [
       {"name": "Series Label", "type": "line" or "bar", "dataKey": "column_key", "color": "#hexcode", "yAxisId": "left" or "right"}
     ]
   }
5. In your Final Answer, present your statistical calculations, trend summaries, policy insights, and the exact chart JSON block.

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
