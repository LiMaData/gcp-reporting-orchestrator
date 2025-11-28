# 🚀 Automated Weekly Reporting Deployment Guide

This guide explains how to deploy the **Weekly Analysis Trigger** using Google Cloud Functions and Cloud Scheduler.

## Prerequisites

1.  Google Cloud SDK (`gcloud`) installed and authenticated.
2.  A GCP Project with billing enabled.
3.  APIs enabled:
    *   Cloud Functions API
    *   Cloud Build API
    *   Cloud Scheduler API
    *   Artifact Registry API

## 1. Deploy the Cloud Function

This function will host the orchestrator code. We deploy the entire `src` directory so the function can access all agents.

Run this command from the **root** of your project (`gcp-reporting-orchestrator/`):

```bash
gcloud functions deploy weekly-analysis-orchestrator \
    --gen2 \
    --runtime=python310 \
    --region=us-central1 \
    --source=. \
    --entry-point=weekly_analysis \
    --trigger-http \
    --allow-unauthenticated \
    --timeout=3600s \
    --memory=2GiB \
    --set-env-vars="SNOWFLAKE_ACCOUNT=your_account,SNOWFLAKE_USER=your_user,SNOWFLAKE_PASSWORD=your_password,SNOWFLAKE_WAREHOUSE=your_warehouse,SNOWFLAKE_DATABASE=your_db,SNOWFLAKE_SCHEMA=your_schema,GOOGLE_API_KEY=your_gemini_key,TEAMS_WEBHOOK_URL=your_webhook_url"
```

**⚠️ Important Notes:**
*   **`--source=.`**: We upload the current directory so `src.agents` are available.
*   **`--timeout=3600s`**: Analysis can take time, so we set a 1-hour timeout (max for Gen 2).
*   **`--memory=2GiB`**: Snowpark and Pandas need memory.
*   **`--set-env-vars`**: You MUST replace the values with your actual credentials from your `.env` file. For production, consider using **Secret Manager**.

## 2. Create the Cloud Scheduler Job

This job will hit the Cloud Function every **Monday at 9:00 AM**.

1.  **Get the Function URL**:
    ```bash
    gcloud functions describe weekly-analysis-orchestrator --region=us-central1 --format="value(serviceConfig.uri)"
    ```
    *(Copy the URL returned, e.g., `https://weekly-analysis-orchestrator-xyz-uc.a.run.app`)*

2.  **Create the Scheduler**:
    ```bash
    gcloud scheduler jobs create http weekly-analysis-job \
        --schedule="0 9 * * 1" \
        --uri="YOUR_FUNCTION_URL_HERE" \
        --http-method=POST \
        --message-body='{"business_question": "Weekly Automated Check: Email Campaign Lift"}' \
        --headers="Content-Type=application/json" \
        --location=us-central1
    ```

## 3. Test the Automation

You can manually trigger the job to test it:

```bash
gcloud scheduler jobs run weekly-analysis-job --location=us-central1
```

Check the **Cloud Functions Logs** to see the orchestrator running!
