terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 4.0.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable necessary APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "bigquery.googleapis.com",
    "cloudfunctions.googleapis.com",
    "run.googleapis.com",
    "workflows.googleapis.com",
    "cloudscheduler.googleapis.com",
    "aiplatform.googleapis.com", # Vertex AI
    "secretmanager.googleapis.com",
    "eventarc.googleapis.com"
  ])
  service = each.key
  disable_on_destroy = false
}

# BigQuery Dataset
resource "google_bigquery_dataset" "ai_insights" {
  dataset_id = "ai_insights"
  location   = var.region
}

# BigQuery Table for Predictions
resource "google_bigquery_table" "predictions" {
  dataset_id = google_bigquery_dataset.ai_insights.dataset_id
  table_id   = "predictions"
  schema     = <<EOF
[
  {
    "name": "prediction_id",
    "type": "STRING",
    "mode": "REQUIRED"
  },
  {
    "name": "timestamp",
    "type": "TIMESTAMP",
    "mode": "REQUIRED"
  },
  {
    "name": "data",
    "type": "JSON",
    "mode": "NULLABLE"
  },
  {
    "name": "status",
    "type": "STRING",
    "mode": "REQUIRED"
  }
]
EOF
}

# Storage Bucket for Function Source Code
resource "google_storage_bucket" "function_source" {
  name          = "${var.project_id}-function-source"
  location      = var.region
  force_destroy = true
}
