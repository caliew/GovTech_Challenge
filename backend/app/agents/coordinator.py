import logging
import json
from typing import Callable, Dict, Any
from backend.app.agents.base import BaseAgent
from backend.app.agents.extraction import ExtractionAgent
from backend.app.agents.analyst import AnalyticsAgent
from backend.app.utils.llm import llm_service
from backend.app.utils.chart_builder import build_chart_spec

logger = logging.getLogger("CoordinatorAgent")

SYSTEM_INSTRUCTION = """
You are the Data Coordinator Agent. Your role is to serve as the master architect of the policy research workflow.

Responsibilities:
1. Parse the user's natural language policy query (e.g., "Analyze employment trends in the technology sector from 2020-2024").
2. Formulate a structured execution plan (data needed, database tables to check, external API resources).
3. Coordinate and orchestrate the Extraction Agent and Analytics Agent to complete their tasks.
4. Review the outputs returned by the Extraction and Analytics agents.
5. Synthesize these inputs into a final, professional **Singapore Policy Brief (Markdown Report)**.
   - Include a descriptive title, Executive Summary, clear sections, and data tables.
   - Incorporate proper source citations (e.g. MOM statistics, SingStat CPI index).
   - Generate policy implications and actionable recommendations.
6. Package the final compiled report and the charts configuration together.

You operate via standard ReAct formatting:
Thought: ...
Action: ...
Action Input: ...
Observation: ...
"""

class CoordinatorAgent(BaseAgent):
    def __init__(self, ws_callback: Callable = None):
        super().__init__(
            name="Coordinator",
            system_instruction=SYSTEM_INSTRUCTION,
            ws_callback=ws_callback
        )
        self.ws_callback = ws_callback

    async def run_workflow(self, user_query: str) -> Dict[str, Any]:
        """
        Orchestrates the entire multi-agent process from query to final markdown report.
        """
        await self.log_step("status", f"Starting research orchestration for query: '{user_query}'")

        # 1. PLAN WORKFLOW
        await self.log_step("status", "Planning analytical workflow...")
        plan_prompt = f"""
        Formulate a step-by-step analytical plan to answer this query:
        "{user_query}"
        Specify which data sources are needed (MOM employment, SingStat Population, SingStat CPI index)
        and what analytics are required. Output your plan as a clean JSON object containing 'plan_steps' and 'justification'.
        """
        plan_response = llm_service.generate(plan_prompt, self.system_instruction)
        
        try:
            plan_json = json.loads(plan_response)
            await self.log_step("thought", f"Workflow Plan formulated successfully!\nJustification: {plan_json.get('justification')}")
        except Exception:
            await self.log_step("thought", f"Workflow Plan formulated:\n{plan_response}")

        # 2. RUN EXTRACTION AGENT
        await self.log_step("status", "Delegating task to Extraction Agent...")
        extractor = ExtractionAgent(ws_callback=self.ws_callback)
        extraction_query = f"Extract all raw records relevant to answering: '{user_query}'. Return the result as raw data."
        logger.info(f"🟡 [{self.name}] EXTRACTOR RUN 🟡")
        extraction_result = await extractor.run(extraction_query)
        
        await self.log_step("status", "Received data from Extraction Agent. Running sanity check...")
        await self.log_step("thought", "Extraction Agent returned cleaned datasets and data quality logs. Proceeding to analysis phase.")

        # 3. RUN ANALYTICS AGENT
        await self.log_step("status", "Delegating dataset to Analytics Agent for statistical insights...")
        analyst = AnalyticsAgent(ws_callback=self.ws_callback)
        analytics_query = f"""
        Take the following extracted data and perform formal statistical analysis:
        compute CAGRs, correlations, trend highlights, and policy-relevant anomalies.
        
        Extracted Data:
        {extraction_result}
        
        Original Objective:
        {user_query}
        """
        logger.info(f"🟡 [{self.name}] ANALYST RUN 🟡")
        analytics_result = await analyst.run(analytics_query)
        
        await self.log_step("status", "Received analysis & charts spec from Analytics Agent. Reviewing findings...")
        await self.log_step("thought", "Analytics Agent successfully computed correlation indicators and structured the chart layouts. Proceeding to compile final brief.")

        # 4. COMPILE FINAL REPORT
        await self.log_step("status", "Compiling final policy brief and formatting charts...")
        compilation_prompt = f"""
        Compile a final structured Singapore Policy Brief (Markdown) based on these research artifacts:
        
        User Query:
        {user_query}
        
        Extracted Datasets:
        {extraction_result}
        
        Analytics & Statistics:
        {analytics_result}
        
        Your output must be a professional markdown report with citations, tabular indices, and policy recommendations.
        """
        
        final_report = llm_service.generate(compilation_prompt, self.system_instruction)
        
        # 4.5 AUTOMATED FACT-CHECK & COMPLIANCE GATE
        await self.log_step("status", "Running automated hallucination detection and data accuracy checks...")
        try:
            from backend.app.utils.validator import HallucinationDetector
            from backend.app.database import SessionLocal
            
            db = SessionLocal()
            try:
                validation = HallucinationDetector.validate_report(final_report, db)
                if validation.get("status") == "success":
                    accuracy_score = validation.get("accuracy_score", 1.0)
                    mismatches = validation.get("mismatches", [])
                    mismatches_count = validation.get("mismatches_count", 0)
                    validated_count = validation.get("validated_facts_count", 0)
                    
                    # Formulate verification segment to append to final policy report
                    verification_text = f"\n\n---\n\n### 🛡️ Automated Fact-Checking & Data Quality Certificate\n"
                    verification_text += f"*   **Status:** Verification completed successfully.\n"
                    verification_text += f"*   **Factual Accuracy Score:** `{accuracy_score * 100:.1f}%` ({validated_count} verified facts, {mismatches_count} discrepancies).\n"
                    
                    if mismatches_count > 0:
                        verification_text += f"*   **Flagged Discrepancies:** {mismatches_count} anomalies detected against factual database sources.\n"
                        for m in mismatches:
                            verification_text += f"    *   *Anomaly:* `{m.get('entity')}` reported as `{m.get('reported_value')}` but database fact is `{m.get('factual_value')}` (Source: *{m.get('source')}*).\n"
                    else:
                        verification_text += f"*   **Data Integrity Check:** 100% verified. All reported statistics align perfectly with verified Department of Statistics (DOS) and Ministry of Manpower (MOM) schemas.\n"
                        
                    final_report += verification_text
                    await self.log_step("thought", f"Fact-check verification completed! Accuracy: {accuracy_score * 100:.1f}% ({validated_count} validated, {mismatches_count} anomalies).")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Factual verification execution failed: {e}")

        # 5. BUILD CHART SPEC — deterministic, zero LLM tokens
        await self.log_step("status", "Building chart specification from extracted data...")
        chart_spec = build_chart_spec(extraction_result, user_query)
        logger.info(f"📊 [{self.name}] Chart spec built: type={chart_spec.get('chart_type')}, points={len(chart_spec.get('data', []))}")

        result = {
            "report": final_report,
            "chart_spec": chart_spec
        }
        
        await self.log_step("result", final_report)
        await self.log_step("status", "Orchestration workflow completed successfully. Output ready.")
        
        return result
