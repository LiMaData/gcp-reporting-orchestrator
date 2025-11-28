resource "google_workflows_workflow" "analysis_orchestration" {
  name          = "analysis_orchestration"
  region        = var.region
  description   = "Orchestrates the analysis and validation process"
  service_account = google_service_account.workflows_sa.email
  source_contents = templatefile("../../src/workflows/analysis.yaml", {})
}

resource "google_service_account" "workflows_sa" {
  account_id   = "workflows-sa"
  display_name = "Workflows Service Account"
}

# Cloud Scheduler to trigger reporting
resource "google_cloud_scheduler_job" "daily_report" {
  name             = "daily-report-trigger"
  description      = "Triggers the reporting function daily"
  schedule         = "0 8 * * *"
  time_zone        = "America/New_York"
  attempt_deadline = "320s"

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions_function.generate_reports.https_trigger_url
    
    oidc_token {
      service_account_email = google_service_account.workflows_sa.email
    }
  }
}
