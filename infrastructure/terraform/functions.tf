# Archive Function Source Code
data "archive_file" "analysis_source" {
  type        = "zip"
  source_dir  = "../../src/functions/analysis"
  output_path = "/tmp/analysis.zip"
}

data "archive_file" "load_source" {
  type        = "zip"
  source_dir  = "../../src/functions/load"
  output_path = "/tmp/load.zip"
}

data "archive_file" "reporting_source" {
  type        = "zip"
  source_dir  = "../../src/functions/reporting"
  output_path = "/tmp/reporting.zip"
}

# Upload to Bucket
resource "google_storage_bucket_object" "analysis_zip" {
  name   = "analysis-${data.archive_file.analysis_source.output_md5}.zip"
  bucket = google_storage_bucket.function_source.name
  source = data.archive_file.analysis_source.output_path
}

resource "google_storage_bucket_object" "load_zip" {
  name   = "load-${data.archive_file.load_source.output_md5}.zip"
  bucket = google_storage_bucket.function_source.name
  source = data.archive_file.load_source.output_path
}

resource "google_storage_bucket_object" "reporting_zip" {
  name   = "reporting-${data.archive_file.reporting_source.output_md5}.zip"
  bucket = google_storage_bucket.function_source.name
  source = data.archive_file.reporting_source.output_path
}

# Deploy Functions
resource "google_cloudfunctions_function" "analyze_data" {
  name        = "analyze_data"
  description = "Connects to Snowflake and runs Cortex AI"
  runtime     = "python39"

  available_memory_mb   = 256
  source_archive_bucket = google_storage_bucket.function_source.name
  source_archive_object = google_storage_bucket_object.analysis_zip.name
  trigger_http          = true
  entry_point           = "analyze_data"
  
  environment_variables = {
    SNOWFLAKE_ACCOUNT = var.snowflake_account
    SNOWFLAKE_USER    = var.snowflake_user
    SNOWFLAKE_PASSWORD = var.snowflake_password
  }
}

resource "google_cloudfunctions_function" "load_results" {
  name        = "load_results"
  description = "Loads validated results to BigQuery"
  runtime     = "python39"

  available_memory_mb   = 256
  source_archive_bucket = google_storage_bucket.function_source.name
  source_archive_object = google_storage_bucket_object.load_zip.name
  trigger_http          = true
  entry_point           = "load_results"
  
  environment_variables = {
    GCP_PROJECT = var.project_id
  }
}

resource "google_cloudfunctions_function" "generate_reports" {
  name        = "generate_reports"
  description = "Generates and distributes reports"
  runtime     = "python39"

  available_memory_mb   = 512
  source_archive_bucket = google_storage_bucket.function_source.name
  source_archive_object = google_storage_bucket_object.reporting_zip.name
  trigger_http          = true # Can also be triggered by Pub/Sub or Scheduler
  entry_point           = "generate_reports"
  
  environment_variables = {
    GCP_PROJECT = var.project_id
  }
}
