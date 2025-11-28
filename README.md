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
*   **Interactive UI**: A premium, unbranded Streamlit interface for configuring and monitoring the pipeline.

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
*   **AI Models**: Google Gemini 2.5 Flash, Anthropic Claude 3.5 Sonnet
*   **Cloud Storage**: Google Cloud Storage (GCS)

---

## 🏁 Getting Started

### Prerequisites

*   Python 3.10 or higher
*   A Snowflake Account with Snowpark enabled
*   Google Cloud Project (for Gemini API and GCS)

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-repo/gcp-reporting-orchestrator.git
    cd gcp-reporting-orchestrator
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements-dev.txt
    ```

3.  **Configure Environment**:
    Create a `.env` file in the root directory with the following credentials:

    ```ini
    # Snowflake Credentials
    SNOWFLAKE_ACCOUNT=your_account
    SNOWFLAKE_USER=your_user
    SNOWFLAKE_PASSWORD=your_password
    SNOWFLAKE_WAREHOUSE=your_warehouse
    SNOWFLAKE_DATABASE=your_db
    SNOWFLAKE_SCHEMA=your_schema
    SNOWFLAKE_ROLE=your_role

    # Google Cloud / Gemini
    GOOGLE_API_KEY=your_gemini_api_key
    GCP_PROJECT_ID=your_project_id
    GCS_BUCKET_NAME=your_bucket_name

    # Email (SMTP)
    SMTP_SERVER=smtp.office365.com
    SMTP_PORT=587
    SMTP_USERNAME=your_email@domain.com
    SMTP_PASSWORD=your_password
    EMAIL_SENDER=your_email@domain.com

    # Recipients
    CMO_EMAIL=cmo@domain.com
    DATA_TEAM_GCS_NOTIFY_EMAIL=data@domain.com
    ```

---

## 🖥️ Usage

1.  **Launch the UI**:
    ```bash
    python -m streamlit run src/ui/app.py
    ```

2.  **Run Analysis**:
    *   Open your browser to `http://localhost:8501`.
    *   Enter your **Business Question**.
    *   Select the **Method** (Logistic Regression).
    *   Click **RUN ANALYSIS**.

3.  **View Results**:
    *   Watch the live progress bar as agents execute.
    *   View key metrics (Lift, Significance) on the dashboard.
    *   Check your email/Teams for the delivered reports.

---

## 📂 Project Structure

```text
gcp-reporting-orchestrator/
├── src/
│   ├── agents/             # The 5 AI Agents
│   │   ├── analyst_agent.py
│   │   ├── executor_agent.py
│   │   ├── interpreter_agent.py
│   │   ├── report_agent.py
│   │   └── distributor_agent.py
│   ├── ui/                 # Streamlit Application
│   │   ├── app.py
│   │   └── style.css
│   └── orchestrator.py     # CLI Entry point
├── docs/                   # Documentation
├── setup/                  # Database setup scripts
├── tests/                  # Unit tests
├── .env                    # Configuration (GitIgnored)
└── requirements-dev.txt    # Python dependencies
```
