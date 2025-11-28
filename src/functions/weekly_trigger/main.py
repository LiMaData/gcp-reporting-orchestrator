import functions_framework
import sys
import os
import json

# Add the root directory to the path so we can import src modules
# In Cloud Functions, the source is usually in the root or a subdir
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.orchestrator import run_orchestrator

@functions_framework.http
def weekly_analysis(request):
    """
    Cloud Function triggered by Cloud Scheduler to run the weekly analysis.
    """
    print("Received weekly analysis trigger")
    
    # Default configuration for the weekly run
    # You can customize this default request
    analysis_request = {
        'table': 'PLAYGROUND_LM.GCP_REPORTING_ORCHESTRATOR.INCREMENTALITY_ANALYSIS_DUMMY',
        'treatment': 'received_email',
        'outcome': 'converted',
        'covariates': ['age_group', 'customer_segment', 'total_purchases', 'recency_bin'],
        'method': 'propensity_score_matching',
        'business_question': 'Weekly Automated Report: What is the incremental lift from the email campaign?'
    }
    
    # Allow overriding parameters via the Scheduler payload
    # This allows you to reuse the same function for different analyses
    if request.is_json:
        request_json = request.get_json(silent=True)
        if request_json:
            print(f"Overriding defaults with: {json.dumps(request_json)}")
            analysis_request.update(request_json)
            
    try:
        # Run the full orchestration pipeline
        run_orchestrator(analysis_request)
        return 'Analysis completed successfully', 200
    except Exception as e:
        print(f"Error executing analysis: {e}")
        # Return 500 so Scheduler knows it failed and can retry
        return f'Analysis failed: {str(e)}', 500
