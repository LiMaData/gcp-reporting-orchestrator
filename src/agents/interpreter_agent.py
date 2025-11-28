"""
Agent 3: Insight Interpreter Agent (Gemini 2.5 Flash)
Analyzes statistical results from Agent 2 and writes business insights to Snowflake.
"""

import os
import json
import logging
from datetime import datetime

# Use Gemini for insights generation
import google.generativeai as genai

# Snowflake connector for persisting insights
try:
    import snowflake.connector
except ImportError:
    snowflake = None


class InterpreterAgent:
    """Insight Interpreter Agent using Gemini and Snowflake persistence."""

    def __init__(self):
        # Load environment variables
        self.snowflake_account = os.getenv("SNOWFLAKE_ACCOUNT")
        self.snowflake_user = os.getenv("SNOWFLAKE_USER")
        self.snowflake_password = os.getenv("SNOWFLAKE_PASSWORD")
        self.snowflake_warehouse = os.getenv("SNOWFLAKE_WAREHOUSE")
        self.snowflake_database = os.getenv("SNOWFLAKE_DATABASE")
        self.snowflake_schema = os.getenv("SNOWFLAKE_SCHEMA")
        self.insights_table = os.getenv("SNOWFLAKE_INSIGHTS_TABLE", "AGENT_INSIGHTS")

        # Basic validation
        if not all([self.snowflake_account, self.snowflake_user, self.snowflake_password,
                    self.snowflake_warehouse, self.snowflake_database, self.snowflake_schema]):
            logging.warning("Snowflake credentials not fully set – persistence will be disabled.")

        # Gemini API key
        self.gemini_api_key = os.getenv("GOOGLE_API_KEY")
        if not self.gemini_api_key:
            logging.warning("GOOGLE_API_KEY not set – InterpreterAgent will use mock insights.")
        else:
            genai.configure(api_key=self.gemini_api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash')

    def interpret_and_store(self, analysis_results):
        """Generate insights from statistical results and store them in Snowflake.

        Args:
            analysis_results (dict): The JSON-serializable output from Agent 2.

        Returns:
            dict: The insights dictionary (including any persistence metadata).
        """
        insights = self._generate_insights(analysis_results)
        # Persist to Snowflake (if credentials are available)
        if self._can_persist():
            try:
                self._save_to_snowflake(insights)
                logging.info("Insights successfully persisted to Snowflake.")
                insights["persistence"] = "snowflake"
            except Exception as e:
                logging.error(f"Failed to persist insights to Snowflake: {e}")
                insights["persistence"] = f"failed: {e}"
        else:
            logging.info("Skipping Snowflake persistence – credentials missing.")
            insights["persistence"] = "skipped"
        return insights

    def _can_persist(self):
        return all([self.snowflake_account, self.snowflake_user, self.snowflake_password,
                    self.snowflake_warehouse, self.snowflake_database, self.snowflake_schema]) and snowflake is not None

    def _generate_insights(self, analysis_results):
        """Call Gemini (or return a mock) to transform raw results into business insights."""
        if not self.gemini_api_key:
            # Mock response
            logging.info("Using mock insights (Gemini API key not available).")
            return {
                "summary": "Mock insight: The treatment shows a positive incremental lift.",
                "key_findings": ["Lift is positive", "Statistically significant", "Effect size modest"],
                "recommendation": "Scale the campaign while monitoring cost per acquisition.",
                "confidence_level": "High",
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "raw_analysis": analysis_results,
                "incremental_lift_pct": analysis_results.get('incremental_lift_pct', 0) if isinstance(analysis_results, dict) else 0,
                "is_significant": analysis_results.get('is_significant', 0) if isinstance(analysis_results, dict) else 0,
                "treatment_effect": analysis_results.get('treatment_effect', 0) if isinstance(analysis_results, dict) else 0,
            }

        # Real Gemini call
        prompt = (
            "You are an expert Marketing Analyst. Analyze the following statistical results from an incrementality test.\n\n"
            f"RESULTS:\n{json.dumps(analysis_results, indent=2)}\n\n"
            "TASK:\n"
            "1. Provide a concise executive summary of the findings\n"
            "2. List 3-5 key findings (as a list)\n"
            "3. Provide a clear business recommendation\n"
            "4. Assess confidence level (High/Medium/Low)\n\n"
            "Output ONLY a JSON object with these exact keys:\n"
            "- summary (string)\n"
            "- key_findings (list of strings)\n"
            "- recommendation (string)\n"
            "- confidence_level (string)\n\n"
            "Do not include any markdown formatting or code blocks, just the raw JSON."
        )
        
        try:
            response = self.model.generate_content(prompt)
            content = response.text.strip()
            
            # Extract JSON if wrapped in markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            insights = json.loads(content)
            insights["generated_at"] = datetime.utcnow().isoformat() + "Z"
            insights["raw_analysis"] = analysis_results
            
            # Promote key metrics to top level for DistributorAgent
            if isinstance(analysis_results, dict):
                insights['incremental_lift_pct'] = analysis_results.get('incremental_lift_pct', 0)
                insights['is_significant'] = analysis_results.get('is_significant', 0)
                insights['treatment_effect'] = analysis_results.get('treatment_effect', 0)
            
            logging.info("Successfully generated insights using Gemini")
            return insights
            
        except Exception as e:
            logging.error(f"Gemini call failed: {e}")
            # Fallback to mock if Gemini errors
            return {
                "summary": f"Error generating insights: {e}",
                "key_findings": [],
                "recommendation": "Review manually.",
                "confidence_level": "Low",
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "raw_analysis": analysis_results,
                "incremental_lift_pct": analysis_results.get('incremental_lift_pct', 0) if isinstance(analysis_results, dict) else 0,
                "is_significant": analysis_results.get('is_significant', 0) if isinstance(analysis_results, dict) else 0,
                "treatment_effect": analysis_results.get('treatment_effect', 0) if isinstance(analysis_results, dict) else 0,
            }

    def _save_to_snowflake(self, insights):
        """Insert the insights dictionary into a Snowflake table as a VARIANT column."""
        ctx = snowflake.connector.connect(
            user=self.snowflake_user,
            password=self.snowflake_password,
            account=self.snowflake_account,
            warehouse=self.snowflake_warehouse,
            database=self.snowflake_database,
            schema=self.snowflake_schema,
        )
        cs = ctx.cursor()
        try:
            import uuid
            insight_id = str(uuid.uuid4())
            
            # Use TO_VARIANT which handles the JSON conversion properly
            # Pass the JSON string as a parameter to avoid SQL injection and escaping issues
            insert_sql = f"""
                INSERT INTO {self.insights_table} (INSIGHT_ID, INSIGHT_DATA)
                SELECT %s, TO_VARIANT(PARSE_JSON(%s))
            """
            cs.execute(insert_sql, (insight_id, json.dumps(insights)))
            ctx.commit()
            logging.info(f"Successfully saved insights to Snowflake with ID: {insight_id}")
        finally:
            cs.close()
            ctx.close()


if __name__ == "__main__":
    sample_results = {
        "treatment_effect": 0.045,
        "p_value": 0.012,
        "confidence_interval": [0.02, 0.07],
        "treated_conversion_rate": 0.18,
        "control_conversion_rate": 0.135,
        "incremental_lift_pct": 33.3,
        "is_significant": True,
        "diagnostics": {"balance": "good"},
    }
    agent = InterpreterAgent()
    insights = agent.interpret_and_store(sample_results)
    print(json.dumps(insights, indent=2))
