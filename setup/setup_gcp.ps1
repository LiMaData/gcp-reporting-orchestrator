# GCP External Stages Setup Script
# Based on next_steps_gcp.md

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "GCP External Stages Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if gcloud is installed
Write-Host "Checking gcloud installation..." -ForegroundColor Yellow
try {
    $null = gcloud version 2>&1
    Write-Host "OK gcloud CLI is installed" -ForegroundColor Green
}
catch {
    Write-Host "ERROR gcloud CLI not found. Please install from: https://cloud.google.com/sdk/docs/install" -ForegroundColor Red
    exit 1
}

# Login to GCP
Write-Host ""
Write-Host "Step 1: Authenticate with GCP" -ForegroundColor Yellow
Write-Host "Running: gcloud auth login" -ForegroundColor Gray
gcloud auth login

# Set project
Write-Host ""
Write-Host "Step 2: Set GCP Project" -ForegroundColor Yellow
$PROJECT_ID = Read-Host "Enter your GCP Project ID"

if ([string]::IsNullOrWhiteSpace($PROJECT_ID)) {
    Write-Host "ERROR Project ID cannot be empty" -ForegroundColor Red
    exit 1
}

gcloud config set project $PROJECT_ID

# Verify project
Write-Host ""
Write-Host "Verifying project access..." -ForegroundColor Yellow
$currentProject = gcloud config get-value project
Write-Host "OK Current project: $currentProject" -ForegroundColor Green

# Enable required APIs
Write-Host ""
Write-Host "Step 3: Enable required GCP APIs" -ForegroundColor Yellow
Write-Host "This may take a few minutes..." -ForegroundColor Gray

gcloud services enable storage-api.googleapis.com
gcloud services enable iam.googleapis.com
gcloud services enable cloudfunctions.googleapis.com

Write-Host "OK APIs enabled" -ForegroundColor Green

# Create GCS Bucket
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Creating GCS Bucket" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$BUCKET_NAME = "incrementality-pipeline-$PROJECT_ID"
$REGION = "us-central1"

Write-Host ""
Write-Host "Bucket name: $BUCKET_NAME" -ForegroundColor Yellow
Write-Host "Region: $REGION" -ForegroundColor Yellow

# Check if bucket exists
$bucketExists = gcloud storage buckets list --filter="name:$BUCKET_NAME" --format="value(name)" 2>&1

if ($bucketExists -like "*$BUCKET_NAME*") {
    Write-Host "OK Bucket already exists: gs://$BUCKET_NAME" -ForegroundColor Green
}
else {
    Write-Host "Creating bucket..." -ForegroundColor Yellow
    gcloud storage buckets create "gs://$BUCKET_NAME" --project=$PROJECT_ID --location=$REGION --uniform-bucket-level-access
    Write-Host "OK Bucket created: gs://$BUCKET_NAME" -ForegroundColor Green
}

# Create directory structure
Write-Host ""
Write-Host "Creating directory structure..." -ForegroundColor Yellow

$directories = @("semantic_models", "generated_code", "reports", "audit_logs")

foreach ($dir in $directories) {
    $placeholder = "# Placeholder for $dir"
    $placeholder | Out-File -FilePath "temp_placeholder.txt" -Encoding utf8
    gcloud storage cp temp_placeholder.txt "gs://$BUCKET_NAME/$dir/.placeholder" 2>&1 | Out-Null
}

Remove-Item "temp_placeholder.txt" -ErrorAction SilentlyContinue

Write-Host "OK Directory structure created" -ForegroundColor Green

# Create Service Account
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Creating Service Account" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$SA_NAME = "incrementality-pipeline-sa"
$SA_EMAIL = "$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

# Check if service account exists
$saExists = gcloud iam service-accounts list --filter="email:$SA_EMAIL" --format="value(email)" 2>&1

if ($saExists -like "*$SA_EMAIL*") {
    Write-Host "OK Service account already exists: $SA_EMAIL" -ForegroundColor Green
}
else {
    Write-Host "Creating service account..." -ForegroundColor Yellow
    gcloud iam service-accounts create $SA_NAME --display-name="Incrementality Pipeline Service Account" --description="Service account for Cloud Functions to access GCS and Snowflake"
    Write-Host "OK Service account created: $SA_EMAIL" -ForegroundColor Green
}

# Grant permissions
Write-Host ""
Write-Host "Granting permissions to service account..." -ForegroundColor Yellow

gcloud storage buckets add-iam-policy-binding "gs://$BUCKET_NAME" --member="serviceAccount:$SA_EMAIL" --role="roles/storage.objectAdmin"

Write-Host "OK Permissions granted" -ForegroundColor Green

# Create Service Account Key
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Creating Service Account Key" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$KEY_FILE = "incrementality-pipeline-key.json"

if (Test-Path $KEY_FILE) {
    Write-Host "WARNING Key file already exists: $KEY_FILE" -ForegroundColor Yellow
    $overwrite = Read-Host "Overwrite existing key? (y/n)"
    if ($overwrite -eq "y") {
        gcloud iam service-accounts keys create $KEY_FILE --iam-account=$SA_EMAIL
        Write-Host "OK Service account key created: $KEY_FILE" -ForegroundColor Green
    }
    else {
        Write-Host "Skipping key creation" -ForegroundColor Gray
    }
}
else {
    gcloud iam service-accounts keys create $KEY_FILE --iam-account=$SA_EMAIL
    Write-Host "OK Service account key created: $KEY_FILE" -ForegroundColor Green
}

Write-Host ""
Write-Host "WARNING IMPORTANT: Keep this key secure! Do not commit to git!" -ForegroundColor Red

# Update .env file
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Updating .env Configuration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$envPath = ".env"
$envContent = ""
if (Test-Path $envPath) {
    $envContent = Get-Content $envPath -Raw
}

$gcpConfig = "`n# ============================================`n# GCP CONFIGURATION (Added by setup script)`n# ============================================`nGCP_PROJECT_ID=$PROJECT_ID`nGCS_BUCKET_NAME=$BUCKET_NAME`nGOOGLE_APPLICATION_CREDENTIALS=$((Get-Location).Path)\$KEY_FILE`n"

if ($envContent -notmatch "GCP_PROJECT_ID") {
    Add-Content -Path $envPath -Value $gcpConfig
    Write-Host "OK .env file updated with GCP configuration" -ForegroundColor Green
}
else {
    Write-Host "WARNING GCP configuration already exists in .env" -ForegroundColor Yellow
}

# Test GCS Access
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Testing GCS Access" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Set environment variable
$env:GOOGLE_APPLICATION_CREDENTIALS = "$((Get-Location).Path)\$KEY_FILE"

# Create test file
"semantic_model_test: true" | Out-File -FilePath "test_semantic_model.yaml" -Encoding utf8

# Upload
Write-Host "Uploading test file..." -ForegroundColor Yellow
gcloud storage cp test_semantic_model.yaml "gs://$BUCKET_NAME/semantic_models/"

# List
Write-Host "Listing files..." -ForegroundColor Yellow
gcloud storage ls "gs://$BUCKET_NAME/semantic_models/"

# Download
Write-Host "Downloading test file..." -ForegroundColor Yellow
gcloud storage cp "gs://$BUCKET_NAME/semantic_models/test_semantic_model.yaml" "./test_download.yaml"

# Verify
$testContent = Get-Content "./test_download.yaml" -Raw
if ($testContent -match "semantic_model_test") {
    Write-Host "OK GCS access working!" -ForegroundColor Green
}
else {
    Write-Host "ERROR GCS test failed" -ForegroundColor Red
}

# Cleanup
Remove-Item "test_semantic_model.yaml" -ErrorAction SilentlyContinue
Remove-Item "test_download.yaml" -ErrorAction SilentlyContinue

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration Summary:" -ForegroundColor Yellow
Write-Host "  Project ID: $PROJECT_ID" -ForegroundColor White
Write-Host "  Bucket: gs://$BUCKET_NAME" -ForegroundColor White
Write-Host "  Service Account: $SA_EMAIL" -ForegroundColor White
Write-Host "  Key File: $KEY_FILE" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Configure Snowflake Storage Integration (see next_steps_gcp.md Step 6)" -ForegroundColor White
Write-Host "  2. Create External Stages in Snowflake (Step 8)" -ForegroundColor White
Write-Host "  3. Upload your semantic model using the helper scripts" -ForegroundColor White
Write-Host ""
