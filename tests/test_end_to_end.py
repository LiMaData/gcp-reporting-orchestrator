"""
End-to-End Test: Agent 1 -> Agent 2 -> Agent 3 -> Agent 4
Goal: Generate a PDF report from a business question.
"""

import os
import sys
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.analyst_agent import AnalystAgent
from src.agents.executor_agent import ExecutorAgent
from src.agents.interpreter_agent import InterpreterAgent
from src.agents.report_agent import ReportGeneratorAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_pdf(html_content, output_path):
    """
    Generate PDF from HTML content.
    Tries to use xhtml2pdf if available.
    """
    try:
        from xhtml2pdf import pisa
        
        with open(output_path, "wb") as result_file:
            pisa_status = pisa.CreatePDF(
                html_content,
                dest=result_file
            )
        
        if pisa_status.err:
            logger.error("PDF generation failed")
            return False
        return True
        
    except ImportError:
        logger.warning("xhtml2pdf not installed. Cannot generate PDF.")
        logger.info("To enable PDF generation, run: pip install xhtml2pdf")
        return False
    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        return False

def main():
    logger.info("STARTING END-TO-END TEST")
    
    # ----------------------------------------------------------------
    # Step 1: Analyst Agent
    # ----------------------------------------------------------------
    logger.info("STEP 1: Analyst Agent - Generating Code")
    analyst = AnalystAgent(semantic_model_path='docs/semantic_model.yaml')
    
    request = {
        'table': 'PLAYGROUND_LM.GCP_REPORTING_ORCHESTRATOR.INCREMENTALITY_ANALYSIS_DUMMY',
        'treatment': 'received_email',
        'outcome': 'converted',
        'covariates': ['customer_segment', 'age_group'],
        'method': 'propensity_score_matching',
        'business_question': 'What is the incremental impact of the email campaign on conversion?'
    }
    
    try:
        analysis_code_result = analyst.generate_analysis_code(request)
        gcs_path = analysis_code_result['gcs_path']
        logger.info(f"Code generated and saved to: {gcs_path}")
    except Exception as e:
        logger.error(f"Step 1 Failed: {e}")
        return

    # ----------------------------------------------------------------
    # Step 2: Executor Agent
    # ----------------------------------------------------------------
    logger.info("STEP 2: Executor Agent - Executing Code")
    executor = ExecutorAgent()
    
    # Note: This might fail if Snowflake credentials are not set or valid.
    # We will handle this by checking the result.
    execution_result = executor.execute_from_gcs(gcs_path, timeout=120)
    
    if not execution_result['success']:
        logger.warning("Execution failed or timed out. Using MOCK results for downstream testing.")
        # Mock results for testing flow if execution fails (e.g. due to connectivity)
        analysis_results = {
            "treatment_effect": 0.052,
            "p_value": 0.003,
            "confidence_interval": [0.041, 0.063],
            "treated_conversion_rate": 0.185,
            "control_conversion_rate": 0.133,
            "incremental_lift_pct": 39.1,
            "sample_sizes": {"treated": 5000, "control": 5000},
            "is_significant": True,
            "diagnostics": {"covariate_balance": "Good"}
        }
    else:
        analysis_results = execution_result['analysis_results']
        logger.info("Execution successful!")

    # ----------------------------------------------------------------
    # Step 3: Interpreter Agent
    # ----------------------------------------------------------------
    logger.info("STEP 3: Interpreter Agent - Generating Insights")
    interpreter = InterpreterAgent()
    insights = interpreter.interpret_and_store(analysis_results)
    logger.info("Insights generated.")

    # ----------------------------------------------------------------
    # Step 4: Report Generator Agent
    # ----------------------------------------------------------------
    logger.info("STEP 4: Report Generator Agent - Creating Report")
    reporter = ReportGeneratorAgent()
    
    # Generate for CMO
    report_data = reporter.generate_report(insights, persona="CMO")
    html_content = report_data['html']
    
    # Save HTML
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    html_filename = f"report_cmo_{timestamp}.html"
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    logger.info(f"HTML Report saved to: {html_filename}")
    
    # Generate PDF
    pdf_filename = f"report_cmo_{timestamp}.pdf"
    if generate_pdf(html_content, pdf_filename):
        logger.info(f"PDF Report saved to: {pdf_filename}")
    else:
        logger.warning("Skipping PDF generation.")

    logger.info("END-TO-END TEST COMPLETE")

if __name__ == "__main__":
    main()
