"""
Full Pipeline End-to-End Test
Tests all 4 agents in sequence with real analysis
"""

import os
import sys
import json
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.analyst_agent import AnalystAgent
from src.agents.executor_agent import ExecutorAgent
from src.agents.interpreter_agent import InterpreterAgent
from src.agents.report_agent import ReportGeneratorAgent

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

print("\n" + "="*80)
print("FULL PIPELINE END-TO-END TEST")
print("="*80)
print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80 + "\n")

# Define the analysis request
request = {
    'table': 'PLAYGROUND_LM.GCP_REPORTING_ORCHESTRATOR.INCREMENTALITY_ANALYSIS_DUMMY',
    'treatment': 'received_email',
    'outcome': 'converted',
    'covariates': ['age_group', 'customer_segment', 'total_purchases', 'recency_bin'],
    'method': 'propensity_score_matching',
    'business_question': 'What is the incremental lift in conversions from the LNP email campaign?'
}

print("Analysis Request:")
print(json.dumps(request, indent=2))
print()

# ============================================================================
# AGENT 1: Analyst Agent (Code Generator)
# ============================================================================
print("\n" + "="*80)
print("AGENT 1: ANALYST (Gemini 2.5 Flash) - Generating Analysis Code")
print("="*80 + "\n")

try:
    analyst = AnalystAgent(semantic_model_path='docs/semantic_model.yaml')
    analyst_result = analyst.generate_analysis_code(request)
    
    print(f"[OK] Code generated successfully")
    print(f"  - Model: {analyst_result['model']}")
    print(f"  - Timestamp: {analyst_result['timestamp']}")
    print(f"  - Valid syntax: {analyst_result['is_valid']}")
    print(f"  - GCS path: {analyst_result.get('gcs_path', 'Not saved')}")
    print(f"  - Code length: {len(analyst_result['code'])} characters")
    
    generated_code = analyst_result['code']
    
except Exception as e:
    print(f"[ERROR] Agent 1 failed: {e}")
    sys.exit(1)

# ============================================================================
# AGENT 2: Executor Agent (Snowflake Execution)
# ============================================================================
print("\n" + "="*80)
print("AGENT 2: EXECUTOR (Snowflake/Snowpark) - Executing Analysis Code")
print("="*80 + "\n")

execution_result = {}
try:
    executor = ExecutorAgent()
    # Use execute_from_gcs if available in analyst_result, otherwise execute_code
    if analyst_result.get('gcs_path'):
        execution_result = executor.execute_from_gcs(analyst_result['gcs_path'], timeout=300)
    else:
        execution_result = executor.execute_code(generated_code, timeout=300)
    
    if execution_result['success']:
        print(f"[OK] Code executed successfully")
        print(f"  - Return code: {execution_result['returncode']}")
        print(f"  - Timestamp: {execution_result['timestamp']}")
        
        analysis_data = execution_result['analysis_results']
        
        if analysis_data:
            print(f"\nAnalysis Results:")
            print(f"  - Treatment effect: {analysis_data.get('treatment_effect', 'N/A')}")
            print(f"  - P-value: {analysis_data.get('p_value', 'N/A')}")
            print(f"  - Significant: {analysis_data.get('is_significant', 'N/A')}")
            print(f"  - Incremental lift: {analysis_data.get('incremental_lift_pct', 'N/A')}%")
        else:
            print("[WARNING] No analysis results parsed from output")
            print("This might be OK if the code prints results differently")
    else:
        print(f"[ERROR] Execution failed")
        print(f"  - Return code: {execution_result['returncode']}")
        print(f"  - Error: {execution_result.get('error', 'Unknown')}")
        if execution_result.get('stderr'):
            print(f"\nStderr (first 500 chars):")
            print(execution_result['stderr'][:500])
        
        # For testing purposes, use mock data if execution fails
        print("\n[INFO] Using mock analysis data for testing downstream agents...")
        analysis_data = {
            "treatment_effect": 0.045,
            "p_value": 0.012,
            "confidence_interval": [0.02, 0.07],
            "treated_conversion_rate": 0.18,
            "control_conversion_rate": 0.135,
            "incremental_lift_pct": 33.3,
            "is_significant": True,
            "sample_sizes": {"treated": 5000, "control": 5000},
            "diagnostics": {"balance": "good"},
        }
        
except Exception as e:
    print(f"[ERROR] Agent 2 failed: {e}")
    # Use mock data for testing
    print("\n[INFO] Using mock analysis data for testing downstream agents...")
    analysis_data = {
        "treatment_effect": 0.045,
        "p_value": 0.012,
        "confidence_interval": [0.02, 0.07],
        "treated_conversion_rate": 0.18,
        "control_conversion_rate": 0.135,
        "incremental_lift_pct": 33.3,
        "is_significant": True,
        "sample_sizes": {"treated": 5000, "control": 5000},
        "diagnostics": {"balance": "good"},
    }

# ============================================================================
# AGENT 3: Interpreter Agent (Insight Generator)
# ============================================================================
print("\n" + "="*80)
print("AGENT 3: INTERPRETER (Gemini 2.5 Flash) - Generating Insights")
print("="*80 + "\n")

try:
    interpreter = InterpreterAgent()
    insights = interpreter.interpret_and_store(analysis_data)
    
    # Check if real or mock insights
    if insights.get('summary', '').startswith('Mock insight'):
        print("[WARNING] Agent 3 is using MOCK insights!")
        print("  - Check GOOGLE_API_KEY environment variable")
    else:
        print("[OK] Real insights generated successfully")
    
    print(f"\nInsights Summary:")
    print(f"  - Summary: {insights.get('summary', 'N/A')[:100]}...")
    print(f"  - Confidence: {insights.get('confidence_level', 'N/A')}")
    print(f"  - Key findings: {len(insights.get('key_findings', []))} items")
    print(f"  - Persistence: {insights.get('persistence', 'N/A')}")
    
except Exception as e:
    print(f"[ERROR] Agent 3 failed: {e}")
    sys.exit(1)

# ============================================================================
# AGENT 4: Reporter Agent (Report Generator)
# ============================================================================
print("\n" + "="*80)
print("AGENT 4: REPORTER (Gemini 2.5 Flash) - Generating Persona Reports")
print("="*80 + "\n")

try:
    reporter = ReportGeneratorAgent()
    
    # Generate all three persona reports
    all_reports = reporter.generate_all_persona_reports(insights, output_format='pdf')
    
    print("Report Generation Results:\n")
    
    personas = ['cmo', 'marketing_ops', 'data_team']
    success_count = 0
    
    for persona_key in personas:
        result = all_reports.get(persona_key, {})
        persona_name = result.get('metadata', {}).get('persona', persona_key.upper())
        
        if 'error' in result:
            print(f"[ERROR] {persona_name}: {result['error']}")
        elif 'gcs_path' in result:
            print(f"[OK] {persona_name}:")
            print(f"  - PDF saved to: {result['gcs_path']}")
            print(f"  - Generated at: {result['metadata']['generated_at']}")
            print(f"  - HTML length: {len(result['html'])} characters")
            success_count += 1
        else:
            print(f"[OK] {persona_name}:")
            print(f"  - HTML generated (not saved to GCS)")
            print(f"  - Generated at: {result['metadata']['generated_at']}")
            print(f"  - HTML length: {len(result['html'])} characters")
            success_count += 1
    
    print(f"\nTotal: {success_count}/{len(personas)} reports generated successfully")
    
except Exception as e:
    print(f"[ERROR] Agent 4 failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*80)
print("PIPELINE TEST COMPLETE")
print("="*80)
print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("\nPipeline Status:")
print(f"  [OK] Agent 1 (Analyst): Code generated")
print(f"  [{'OK' if execution_result.get('success') else 'WARN'}] Agent 2 (Executor): {'Executed successfully' if execution_result.get('success') else 'Used mock data'}")
print(f"  [OK] Agent 3 (Interpreter): Insights generated")
print(f"  [OK] Agent 4 (Reporter): {success_count}/{len(personas)} reports generated")
print("\n" + "="*80 + "\n")

# Save full results
output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
os.makedirs(output_dir, exist_ok=True)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
output_file = os.path.join(output_dir, f"pipeline_test_result_{timestamp}.json")

full_result = {
    "request": request,
    "agent1_result": {
        "timestamp": analyst_result['timestamp'],
        "model": analyst_result['model'],
        "is_valid": analyst_result['is_valid'],
        "gcs_path": analyst_result.get('gcs_path'),
        "code_length": len(generated_code)
    },
    "agent2_result": {
        "success": execution_result.get('success'),
        "timestamp": execution_result.get('timestamp'),
        "analysis_data": analysis_data
    },
    "agent3_result": {
        "insights": insights,
        "is_mock": insights.get('summary', '').startswith('Mock insight')
    },
    "agent4_result": {
        "reports_generated": success_count,
        "total_personas": len(personas),
        "reports": {k: {"gcs_path": v.get('gcs_path'), "persona": v.get('metadata', {}).get('persona')} 
                   for k, v in all_reports.items()}
    },
    "test_timestamp": timestamp
}

with open(output_file, 'w') as f:
    json.dump(full_result, f, indent=2)

print(f"Full results saved to: {output_file}\n")
