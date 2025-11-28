import os
import json
from google.cloud import bigquery
import datetime

def load_results(request):
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.
    Returns:
        Response object
    """
    request_json = request.get_json(silent=True)
    if not request_json or 'data' not in request_json:
        return 'No data provided', 400

    data = request_json['data']
    
    # Construct rows to insert
    rows_to_insert = []
    timestamp = datetime.datetime.utcnow().isoformat()
    
    for item in data:
        rows_to_insert.append({
            "prediction_id": item.get("id"),
            "timestamp": timestamp,
            "data": json.dumps(item),
            "status": "VALIDATED"
        })

    client = bigquery.Client()
    table_id = f"{os.environ.get('GCP_PROJECT')}.ai_insights.predictions"

    errors = client.insert_rows_json(table_id, rows_to_insert)
    if errors == []:
        print("New rows have been added.")
        return 'Success', 200
    else:
        print("Encountered errors while inserting rows: {}".format(errors))
        return 'Error inserting rows', 500
