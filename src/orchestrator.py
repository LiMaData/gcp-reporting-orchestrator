import os
import json
import sys
from dotenv import load_dotenv

# Add project root to path so we can import src.agents
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.analyst_agent import AnalystAgent
from src.agents.executor_agent import ExecutorAgent
from src.agents.interpreter_agent import InterpreterAgent
from src.agents.report_agent import ReportGeneratorAgent
from src.agents.distributor_agent import DistributorAgent

def run_orchestrator(request):
    print("Starting Orchestrator...")
    
    # Step 1: Analyst Agent
    print("\nStep 1: Analyst Agent (Gemini)...")
    try:
        analyst = AnalystAgent(semantic_model_path='docs/semantic_model.yaml')
        analyst_result = analyst.generate_analysis_code(request)
        code = analyst_result['code']
        print("Code generated.")
    except Exception as e:
        print(f"Analyst Agent failed: {e}")
        return
    
    # Step 2: Executor Agent
    print("\nStep 2: Executor Agent (Snowpark)...")
    executor = ExecutorAgent()
    # Use execute_from_gcs if available, otherwise execute_code
    if analyst_result.get('gcs_path'):
        execution_result = executor.execute_from_gcs(analyst_result['gcs_path'])
    else:
        execution_result = executor.execute_as_stored_procedure(code)
    
    if not execution_result['success']:
        print("Execution failed.")
        print(f"Error: {execution_result.get('error')}")
        if execution_result.get('stdout'):
            print(f"Stdout: {execution_result.get('stdout')}")
        return
        
    analysis_data = execution_result['analysis_results']
    print("Analysis complete.")
    
    # Step 3: Interpreter Agent
    print("\nStep 3: Interpreter Agent (Claude)...")
    interpreter = InterpreterAgent()
    insights = interpreter.interpret_and_store(analysis_data)
    print("Insights generated.")
    
    # Step 4: Reporter Agent
    print("\nStep 4: Reporter Agent (Gemini)...")
    reporter = ReportGeneratorAgent()
    reports = reporter.generate_all_persona_reports(insights, output_format='pdf')
    print("Reports generated.")
    
    # Step 5: Distributor Agent
    print("\nStep 5: Distributor Agent (Delivery)...")
    distributor = DistributorAgent()
    distribution_results = distributor.distribute_reports(
        all_reports=reports,
        insights=insights,
        metadata={
            'request': request,
            'analyst_result': analyst_result,
            'execution_result': execution_result
        }
    )
    print("Distribution complete.")
    
    # Save outputs
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(base_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, "final_report.json")
    with open(output_file, "w") as f:
        json.dump({
            "request": request,
            "analysis_data": analysis_data,
            "insights": insights,
            "reports": reports,
            "distribution": distribution_results
        }, f, indent=2)
        
    print(f"\nWorkflow complete! Results saved to {output_file}")

if __name__ == "__main__":
    load_dotenv()
    
    # Define the request
    request = {
        'table': 'PLAYGROUND_LM.GCP_REPORTING_ORCHESTRATOR.INCREMENTALITY_ANALYSIS_DUMMY',
        'treatment': 'received_email',
        'outcome': 'converted',
        'covariates': ['age_group', 'customer_segment', 'total_purchases', 'recency_bin'],
        'method': 'propensity_score_matching',
        'business_question': 'What is the incremental lift in conversions from the LNP email campaign?'
    }
    
    run_orchestrator(request)
