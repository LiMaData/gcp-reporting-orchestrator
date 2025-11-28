# GCP Reporting Orchestrator
### AI-Powered Incrementality Analysis Pipeline

The **GCP Reporting Orchestrator** is an autonomous AI agent system designed to perform end-to-end causal inference and incrementality analysis. It connects directly to your Snowflake data warehouse, generates statistical analysis code on the fly, executes it securely, and distributes tailored reports to stakeholders.

---

## 🚀 Key Features

*   **Automated Causal Inference**: Uses AI to generate Python code for Propensity Score Matching (PSM), Logistic Regression, and other causal methods.
*   **Secure Execution**: Runs analysis code directly inside Snowflake using **Snowpark Stored Procedures**, ensuring data never leaves the secure warehouse.
*   **Persona-Specific Reporting**: Generates distinct PDF reports for different stakeholders:
    *   **CMO**: High-level executive summary and strategic recommendations.
    *   **Marketing Ops**: Actionable tactical insights.
    *   **Data Team**: Technical details, code, and statistical diagnostics.
*   **Multi-Channel Distribution**: Automatically sends reports via **Email** (SMTP) and **Microsoft Teams** webhooks.
*   **Fully Automated**: Runs on a weekly schedule using **Google Cloud Functions** and **Cloud Scheduler**.
*   **Interactive UI**: A premium, unbranded Streamlit interface for ad-hoc analysis and monitoring.

---

## 🏗️ Architecture: The 5-Agent System

The pipeline is composed of five specialized AI agents working in sequence:

1.  **🤖 Analyst Agent (Gemini 2.5 Flash)**
    *   Translates business questions (e.g., "What is the lift of the email campaign?") into robust Python/Snowpark code.
    *   Handles feature engineering, one-hot encoding, and statistical modeling.

2.  **⚙️ Executor Agent (Snowpark)**
    *   Deploys the generated code as a temporary Stored Procedure in Snowflake.
    *   Executes the analysis on live data and returns structured JSON results.

3.  **🧠 Interpreter Agent (Claude 3.5 / Gemini)**
    *   Analyzes the raw statistical output (p-values, lift, confidence intervals).
    *   Generates human-readable business insights and recommendations.

4.  **📄 Reporter Agent (Gemini 2.5 Flash)**
    *   Takes the insights and crafts HTML/PDF reports tailored to specific personas (CMO, Ops, Data).

5.  **📨 Distributor Agent**
    *   Routes the final artifacts to the right channels:
        *   **CMO**: Email with PDF attachment.
        *   **Marketing Ops**: Teams notification + Email.
        *   **Data Team**: Email with PDF + Python Source Code.

---

## 🛠️ Tech Stack

*   **Frontend**: [Streamlit](https://streamlit.io/)
*   **Backend**: Python 3.10+
*   **Data Warehouse**: [Snowflake](https://www.snowflake.com/) (Snowpark Python)
*   **AI Models**: Google Gemini 2.5 Flash
*   **Cloud Infrastructure**: 
    *   Google Cloud Functions (2nd Gen)
    *   Google Cloud Scheduler
    *   Google Cloud Storage (GCS)

---

## 🏁 Getting Started

### Prerequisites

*   Python 3.10 or higher
*   A Snowflake Account with Snowpark enabled
*   Google Cloud Project (for Gemini API, Cloud Functions, and GCS)
*   Google Cloud CLI (`gcloud`) installed

### 1. Local Development (Streamlit UI)

Use this for testing, development, and ad-hoc analysis.

1.  **Install dependencies**:
    ```bash
    pip install -r requirements-dev.txt
    ```

2.  **Configure Environment**:
    Create a `.env` file in the root directory (see `.env.example`).

3.  **Launch the UI**:
    ```bash
    python -m streamlit run src/ui/app.py
    ```

4.  **Run Analysis**:
    *   Open your browser to `http://localhost:8501`.
    *   Enter your **Business Question**.
    *   Click **RUN ANALYSIS**.

### 2. Automated Deployment (Cloud Functions)

Use this to run the pipeline automatically on a schedule (e.g., every Monday).

1.  **Deploy the Cloud Function**:
    Run the following command (replace placeholders with your actual values):

    ```bash
    gcloud functions deploy weekly-analysis-orchestrator \
        --gen2 \
        --runtime=python310 \
        --region=us-central1 \
        --source=. \
        --entry-point=weekly_analysis_entry \
        --trigger-http \
        --allow-unauthenticated \
        --timeout=3600s \
        --memory=2GiB \
        --set-env-vars="SNOWFLAKE_ACCOUNT=...,SNOWFLAKE_USER=...,SNOWFLAKE_PASSWORD=...,GOOGLE_API_KEY=...,TEAMS_WEBHOOK_URL=...,GCS_BUCKET_NAME=...SMTP_SERVER=...,SMTP_USERNAME=...,SMTP_PASSWORD=...,CMO_EMAIL=...,DATA_TEAM_GCS_NOTIFY_EMAIL=..."
    ```

2.  **Create the Schedule**:
    Set up a weekly trigger (e.g., every Monday at 9 AM):

    ```bash
    gcloud scheduler jobs create http weekly-analysis-job \
        --schedule="0 9 * * 1" \
        --uri="YOUR_FUNCTION_URL" \
        --http-method=POST \
        --message-body='{"business_question": "Weekly Automated Check: Email Campaign Lift"}' \
        --headers="Content-Type=application/json" \
        --location=us-central1
    ```

3.  **Manual Trigger**:
    Test the automation immediately:
    ```bash
    gcloud scheduler jobs run weekly-analysis-job --location=us-central1
    ```

---

## 📂 Project Structure

```text
gcp-reporting-orchestrator/
├── src/
│   ├── agents/             # The 5 AI Agents
│   ├── functions/          # Cloud Function Entry Points
│   │   └── weekly_trigger/
│   ├── ui/                 # Streamlit Application
│   └── orchestrator.py     # Main Pipeline Logic
├── docs/                   # Documentation & Guides
├── infrastructure/         # Terraform & Setup Scripts
├── .env                    # Local Configuration (GitIgnored)
├── main.py                 # Cloud Function Root Entry Point
├── requirements.txt        # Production Dependencies
└── requirements-dev.txt    # Development Dependencies
```
