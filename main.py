import functions_framework
from src.functions.weekly_trigger.main import weekly_analysis

# Expose the function at the top level
# This allows Cloud Functions to find it when deploying from root
@functions_framework.http
def weekly_analysis_entry(request):
    return weekly_analysis(request)
