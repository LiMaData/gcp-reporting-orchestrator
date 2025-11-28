import os
import json
from google.cloud import bigquery
import vertexai
from vertexai.preview.generative_models import GenerativeModel

def generate_reports(request):
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.
    Returns:
        Response object
    """
    # 1. Query BigQuery for latest data
    client = bigquery.Client()
    query = """
        SELECT data, timestamp 
        FROM `ai_insights.predictions` 
        WHERE status = 'VALIDATED' 
        ORDER BY timestamp DESC 
        LIMIT 10
    """
    query_job = client.query(query)
    results = [json.loads(row["data"]) for row in query_job]

    if not results:
        return "No new data to report", 200

    # 2. Generate Content with Vertex AI
    vertexai.init(project=os.environ.get('GCP_PROJECT'), location="us-central1")
    model = GenerativeModel("gemini-pro")
    
    prompt = f"""
    You are a business analyst. Based on the following data: {json.dumps(results)}, 
    generate a brief executive summary for the leadership team.
    """
    
    response = model.generate_content(prompt)
    summary = response.text
    print(f"Generated Summary: {summary}")

    # 3. Distribute (Mocked)
    print("Sending email to leadership...")
    print("Posting to Slack...")

    return f"Reports generated and sent. Summary: {summary}", 200
