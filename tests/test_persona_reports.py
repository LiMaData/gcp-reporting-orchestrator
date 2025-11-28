"""
Test Agent 4 - Check if different personas generate different reports
"""

import os
import sys
import json
import logging
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.report_agent import ReportGeneratorAgent

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Sample insights (from Agent 3)
sample_insights = {
    "summary": "The incrementality test demonstrated a statistically significant positive lift in conversion rate due to the treatment. The treated group showed a 41.2% incremental lift compared to the control.",
    "key_findings": [
        "Treatment effect of 5.4 percentage points is statistically significant (p=0.008)",
        "Confidence interval [4.1%, 6.7%] indicates robust positive impact",
        "Excellent covariate balance achieved through matching (SMD: 0.15 → 0.03)",
        "Strong common support overlap ensures valid comparisons"
    ],
    "recommendation": "Scale the email campaign immediately. The 41% lift is substantial and statistically robust. Monitor cost per acquisition and maintain data quality standards.",
    "confidence_level": "High",
    "generated_at": "2025-11-26T06:44:00Z"
}

print("\n" + "="*80)
print("TESTING AGENT 4 - PERSONA-SPECIFIC REPORTS")
print("="*80 + "\n")

reporter = ReportGeneratorAgent()

# Test each persona individually
personas = {
    'cmo': 'CMO',
    'marketing_ops': 'Marketing Ops',
    'data_team': 'Data Team'
}

results = {}

for key, persona_name in personas.items():
    print(f"\n{'='*80}")
    print(f"Generating report for: {persona_name}")
    print(f"{'='*80}\n")
    
    result = reporter.generate_report(sample_insights, persona=persona_name, output_format='html')
    results[key] = result
    
    print(f"Persona: {result['metadata']['persona']}")
    print(f"Generated at: {result['metadata']['generated_at']}")
    print(f"Mock: {result['metadata']['mock']}")
    print(f"\nHTML Preview (first 300 chars):")
    print(result['html'][:300])
    print("...\n")

# Check if reports are different
print("\n" + "="*80)
print("VALIDATION: Are reports different for each persona?")
print("="*80 + "\n")

cmo_html = results['cmo']['html']
ops_html = results['marketing_ops']['html']
data_html = results['data_team']['html']

if cmo_html == ops_html == data_html:
    print("[ERROR] All three reports are IDENTICAL!")
    print("This is a BUG - each persona should have different content.\n")
elif cmo_html == ops_html or cmo_html == data_html or ops_html == data_html:
    print("[WARNING] Some reports are identical!")
    if cmo_html == ops_html:
        print("  - CMO and Marketing Ops reports are the same")
    if cmo_html == data_html:
        print("  - CMO and Data Team reports are the same")
    if ops_html == data_html:
        print("  - Marketing Ops and Data Team reports are the same")
    print()
else:
    print("[OK] All three reports are DIFFERENT!")
    print("Each persona has unique content tailored to their needs.\n")

# Show key differences
print("\n" + "="*80)
print("CONTENT ANALYSIS")
print("="*80 + "\n")

for key, persona_name in personas.items():
    html = results[key]['html']
    print(f"{persona_name}:")
    print(f"  - Length: {len(html)} characters")
    print(f"  - Contains 'CMO': {'Yes' if 'CMO' in html else 'No'}")
    print(f"  - Contains 'Marketing Ops': {'Yes' if 'Marketing Ops' in html else 'No'}")
    print(f"  - Contains 'Data Team': {'Yes' if 'Data Team' in html else 'No'}")
    print(f"  - Contains 'ROI': {'Yes' if 'ROI' in html.upper() else 'No'}")
    print(f"  - Contains 'statistical': {'Yes' if 'statistical' in html.lower() else 'No'}")
    print(f"  - Contains 'implementation': {'Yes' if 'implementation' in html.lower() else 'No'}")
    print()

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80 + "\n")
