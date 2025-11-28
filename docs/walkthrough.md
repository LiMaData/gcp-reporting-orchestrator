# Serverless AI Insights and Reporting Engine - Walkthrough

This project implements a serverless, event-driven architecture for predictive analysis and automated reporting using GCP and Snowflake.

## Architecture Components

1.  **Cloud Functions**:
    - `analyze_data`: Connects to Snowflake (mocked) to run Cortex AI predictions.
    - `load_results`: Loads validated predictions into BigQuery.
    - `generate_reports`: Generates summaries using Vertex AI and distributes them.
2.  **Cloud Workflows**:
    - `analysis_orchestration`: Manages the flow from Analysis -> Human Validation -> BigQuery Load.
3.  **Cloud Run UI**:
    - A simple Flask app for business users to approve/reject analysis results.
4.  **Infrastructure**:
    - Terraform configuration to deploy all resources.

## Directory Structure

- `infrastructure/terraform/`: Terraform files (`main.tf`, `functions.tf`, `workflows.tf`, `ui.tf`).
- `src/functions/`: Python source code for Cloud Functions.
- `src/workflows/`: YAML definition for Cloud Workflows.
- `src/ui/`: Python source code for the Validation UI.

## Deployment Instructions

1.  **Prerequisites**:
    - GCP Project with Billing enabled.
    - Terraform installed.
    - Google Cloud SDK installed and authenticated.

2.  **Configuration**:
    - Edit `infrastructure/terraform/variables.tf` or create a `terraform.tfvars` file with your `project_id`, `snowflake_account`, etc.

3.  **Deploy**:
    ```bash
    cd infrastructure/terraform
    terraform init
    terraform apply
    ```

4.  **Build UI Container** (Manual Step for Prototype):
    - Build the `src/ui` image and push to GCR.
    - Update `infrastructure/terraform/ui.tf` with the image URL.

## Verification

- Run unit tests:
  ```bash
  python tests/test_functions.py
  ```
- Trigger the workflow via GCP Console or API to test the end-to-end flow.
