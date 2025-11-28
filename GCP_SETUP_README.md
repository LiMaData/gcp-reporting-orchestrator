# GCP External Stages Setup Guide

This guide will help you set up GCS (Google Cloud Storage) external stages for your Snowflake incrementality analysis pipeline.

## 📋 Prerequisites

- [ ] GCP account with billing enabled
- [ ] Snowflake account with SYSADMIN access (ACCOUNTADMIN for storage integration)
- [ ] gcloud CLI installed ([install guide](https://cloud.google.com/sdk/docs/install))
- [ ] Python 3.8+ with pip

## 🚀 Quick Start

### Step 1: Run GCP Setup Script

This will authenticate with GCP, create a bucket, service account, and configure permissions.

```powershell
# Run the setup script
.\setup_gcp.ps1
```

The script will:
1. Authenticate you with GCP
2. Create a GCS bucket named `incrementality-pipeline-YOUR-PROJECT-ID`
3. Create a service account for the pipeline
4. Generate a service account key file
5. Update your `.env` file with GCP configuration
6. Test GCS access

**Important**: Keep the generated `incrementality-pipeline-key.json` file secure!

### Step 2: Configure Snowflake Storage Integration

1. Open the `setup_snowflake_stages.sql` file
2. Replace `YOUR-PROJECT-ID` with your actual GCP project ID (in 3 places)
3. Run the SQL script in Snowflake (requires ACCOUNTADMIN role)

```sql
-- In Snowflake, run:
!source setup_snowflake_stages.sql
```

4. **CRITICAL**: Copy the `STORAGE_GCP_SERVICE_ACCOUNT` value from the output

### Step 3: Grant Snowflake Access to GCS

Use the service account from Step 2:

```powershell
# Replace with the service account from Snowflake
$SNOWFLAKE_SA = "paste-service-account-here@gcp-project.iam.gserviceaccount.com"
$PROJECT_ID = "your-gcp-project-id"
$BUCKET_NAME = "incrementality-pipeline-$PROJECT_ID"

# Grant access
gcloud storage buckets add-iam-policy-binding gs://$BUCKET_NAME `
    --member="serviceAccount:$SNOWFLAKE_SA" `
    --role="roles/storage.objectAdmin"
```

### Step 4: Upload Semantic Model

```powershell
# Activate your virtual environment
.\.venv\Scripts\Activate.ps1

# Upload the semantic model
python upload_semantic_model.py
```

### Step 5: Verify in Snowflake

```sql
-- List files in the stage
LIST @SEMANTIC_MODELS;

-- Read the semantic model
SELECT $1 FROM @SEMANTIC_MODELS/semantic_model_latest.yaml;
```

## 📁 Project Structure

```
gcp-reporting-orchestrator/
├── setup_gcp.ps1                    # GCP setup automation
├── setup_snowflake_stages.sql       # Snowflake stage creation
├── upload_semantic_model.py         # Upload semantic model to GCS
├── src/
│   └── gcs_snowflake_helper.py     # Python helper library
├── docs/
│   ├── semantic_model.yaml          # Your semantic model
│   └── next_steps_gcp.md           # Detailed guide
└── incrementality-pipeline-key.json # Service account key (DO NOT COMMIT!)
```

## 🔧 Configuration

Your `.env` file should now include:

```bash
# GCP Configuration
GCP_PROJECT_ID=your-gcp-project-id
GCS_BUCKET_NAME=incrementality-pipeline-your-gcp-project-id
GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\incrementality-pipeline-key.json

# Snowflake Configuration
SNOWFLAKE_ACCOUNT=fvqlqib-tj68700
SNOWFLAKE_USER=LIMA
SNOWFLAKE_PASSWORD=Easy2snowflake!
SNOWFLAKE_WAREHOUSE=TEST
SNOWFLAKE_DATABASE=PLAYGROUND_LM
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_ROLE=SYSADMIN
```

## 🧪 Testing

### Test GCS Access

```python
from src.gcs_snowflake_helper import GCSSnowflakeHelper
from dotenv import load_dotenv

load_dotenv()
helper = GCSSnowflakeHelper()

# Upload semantic model
result = helper.upload_semantic_model("docs/semantic_model.yaml")
print(result)

# Download semantic model
model = helper.download_semantic_model()
print(model['table']['name'])
```

### Test Snowflake Stages

```sql
-- In Snowflake
USE ROLE SYSADMIN;
USE WAREHOUSE TEST;
USE DATABASE PLAYGROUND_LM;
USE SCHEMA PUBLIC;

-- List all stages
SHOW STAGES;

-- Test each stage
LIST @SEMANTIC_MODELS;
LIST @GENERATED_CODE;
LIST @REPORTS;
```

## 🔐 Security Best Practices

1. **Never commit** `incrementality-pipeline-key.json` to git
2. Add to `.gitignore`:
   ```
   incrementality-pipeline-key.json
   *.json
   !package.json
   ```
3. Rotate service account keys regularly
4. Use least-privilege IAM roles
5. Enable audit logging in GCS

## 🐛 Troubleshooting

### "Permission denied" when accessing GCS

**Solution**: Verify service account has `roles/storage.objectAdmin`:
```powershell
gcloud storage buckets get-iam-policy gs://incrementality-pipeline-YOUR-PROJECT-ID
```

### "File not found" in Snowflake stage

**Solution**: 
1. Verify file exists in GCS: `gcloud storage ls gs://incrementality-pipeline-YOUR-PROJECT-ID/semantic_models/`
2. Check Snowflake service account has access (Step 3)
3. Refresh stage: `ALTER STAGE SEMANTIC_MODELS REFRESH;`

### "Storage integration not found"

**Solution**: You need ACCOUNTADMIN role to create storage integrations. Contact your Snowflake admin.

## 📚 Next Steps

1. ✅ Complete GCP setup
2. ✅ Configure Snowflake stages
3. ✅ Upload semantic model
4. 🔄 Update agents to use GCS helper library
5. 🔄 Deploy Cloud Functions (optional)
6. 🔄 Set up Cloud Scheduler for automation

## 📖 Additional Resources

- [Full setup guide](docs/next_steps_gcp.md)
- [Snowflake External Stages](https://docs.snowflake.com/en/user-guide/data-load-gcs-config)
- [GCS IAM Permissions](https://cloud.google.com/storage/docs/access-control/iam-permissions)

## 🆘 Need Help?

If you encounter issues:
1. Check the detailed guide: `docs/next_steps_gcp.md`
2. Verify all prerequisites are met
3. Review error messages carefully
4. Check IAM permissions in both GCP and Snowflake
