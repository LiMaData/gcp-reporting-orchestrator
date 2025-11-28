resource "google_cloud_run_service" "validation_ui" {
  name     = "validation-ui"
  location = var.region

  template {
    spec {
      containers {
        image = "us-docker.pkg.dev/cloudrun/container/hello" # Placeholder
        # In a real deployment, you would build the image from src/ui and push to GCR/Artifact Registry
        env {
            name = "GCP_PROJECT"
            value = var.project_id
        }
      }
    }
  }

  traffic {
    percent = 100
    latest_revision = true
  }
}

# Allow unauthenticated access for the demo UI
resource "google_cloud_run_service_iam_member" "public_access" {
  service  = google_cloud_run_service.validation_ui.name
  location = google_cloud_run_service.validation_ui.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
