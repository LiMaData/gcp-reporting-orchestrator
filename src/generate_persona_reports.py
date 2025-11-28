"""
Generate Persona-Specific Reports
Generates PDF reports for CMO, Marketing Ops, and Data Team and saves them to GCS.
"""

import os
import sys
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.agents.report_agent import ReportGeneratorAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    load_dotenv()
    
    # Sample insights (normally this comes from Agent 3)
    insights = {
        "summary": "The email campaign 'Summer Sale 2025' drove a 5.4% incremental lift in conversion rate compared to the control group.",
        "key_findings": [
            "Incremental lift of 5.4% is statistically significant (p-value < 0.01).",
            "Cost per Incremental Acquisition (CPIA) was $12.50, well below the target of $15.00.",
            "The effect was strongest in the 'Loyal Customers' segment (8.2% lift)."
        ],
        "recommendation": "Scale the campaign to the full audience, prioritizing the 'Loyal Customers' segment. Consider testing new creatives for the 'New Users' segment where lift was lower.",
        "confidence_level": "High",
        "generated_at": datetime.now().isoformat()
    }
    
    agent = ReportGeneratorAgent()
    
    personas = ["CMO", "Marketing Ops", "Data Team"]
    
    print("\n" + "="*80)
    print("GENERATING PERSONA-SPECIFIC REPORTS")
    print("="*80 + "\n")
    
    for persona in personas:
        logging.info(f"Generating report for: {persona}")
        
        try:
            result = agent.generate_report(insights, persona=persona, output_format='pdf')
            
            if 'gcs_path' in result:
                print(f"[OK] {persona} Report saved to: {result['gcs_path']}")
            else:
                print(f"[WARNING] {persona} Report generated but GCS upload failed (check logs).")
                
        except Exception as e:
            logging.error(f"Failed to generate report for {persona}: {e}")
            
    print("\n" + "="*80)
    print("DONE")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
