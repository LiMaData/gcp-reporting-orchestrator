-- ============================================================================
-- Snowflake External Stages Setup
-- Based on next_steps_gcp.md
-- ============================================================================

-- IMPORTANT: This script requires ACCOUNTADMIN role for storage integration
-- If you don't have ACCOUNTADMIN, ask your Snowflake admin to run Step 1

-- ============================================================================
-- STEP 1: CREATE STORAGE INTEGRATION (Requires ACCOUNTADMIN)
-- ============================================================================

USE ROLE ACCOUNTADMIN;

-- Replace YOUR-PROJECT-ID with your actual GCP project ID
CREATE OR REPLACE STORAGE INTEGRATION GCS_INCREMENTALITY_INTEGRATION
    TYPE = EXTERNAL_STAGE
    STORAGE_PROVIDER = 'GCS'
    ENABLED = TRUE
    STORAGE_ALLOWED_LOCATIONS = ('gcs://incrementality-pipeline-YOUR-PROJECT-ID/')
    COMMENT = 'Integration for incrementality analysis pipeline with GCS';

-- Grant usage to SYSADMIN role
GRANT USAGE ON INTEGRATION GCS_INCREMENTALITY_INTEGRATION TO ROLE SYSADMIN;

-- Get the Snowflake service account (IMPORTANT - Copy this!)
DESC STORAGE INTEGRATION GCS_INCREMENTALITY_INTEGRATION;

-- ⚠️ CRITICAL: Copy the STORAGE_GCP_SERVICE_ACCOUNT value from above
-- It will look like: service-account-name@gcp-project.iam.gserviceaccount.com
-- You need to grant this service account access to your GCS bucket in GCP

-- ============================================================================
-- STEP 2: CREATE EXTERNAL STAGES (Can be run by SYSADMIN)
-- ============================================================================

USE ROLE SYSADMIN;
USE WAREHOUSE TEST;
USE DATABASE PLAYGROUND_LM;
USE SCHEMA PUBLIC;  -- Using PUBLIC schema since GCP_REPORTING_ORCHESTRATOR is a table

-- Create external stages pointing to GCS
-- Replace YOUR-PROJECT-ID with your actual GCP project ID

CREATE OR REPLACE STAGE SEMANTIC_MODELS
    URL = 'gcs://incrementality-pipeline-YOUR-PROJECT-ID/semantic_models/'
    STORAGE_INTEGRATION = GCS_INCREMENTALITY_INTEGRATION
    DIRECTORY = (ENABLE = TRUE)
    FILE_FORMAT = (TYPE = 'CSV')
    COMMENT = 'External stage for semantic models (YAML/JSON) in GCS';

CREATE OR REPLACE STAGE GENERATED_CODE
    URL = 'gcs://incrementality-pipeline-YOUR-PROJECT-ID/generated_code/'
    STORAGE_INTEGRATION = GCS_INCREMENTALITY_INTEGRATION
    DIRECTORY = (ENABLE = TRUE)
    FILE_FORMAT = (TYPE = 'CSV')
    COMMENT = 'External stage for generated Python code in GCS';

CREATE OR REPLACE STAGE REPORTS
    URL = 'gcs://incrementality-pipeline-YOUR-PROJECT-ID/reports/'
    STORAGE_INTEGRATION = GCS_INCREMENTALITY_INTEGRATION
    DIRECTORY = (ENABLE = TRUE)
    FILE_FORMAT = (TYPE = 'CSV')
    COMMENT = 'External stage for generated reports in GCS';

-- Create internal stages for data that stays in Snowflake
CREATE OR REPLACE STAGE ANALYSIS_RESULTS
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'Internal stage for analysis results';

CREATE OR REPLACE STAGE AUDIT_LOGS
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'Internal stage for audit logs';

-- Verify stages
SHOW STAGES IN SCHEMA PUBLIC;

-- ============================================================================
-- STEP 3: TEST THE INTEGRATION
-- ============================================================================

-- Test 1: List files in GCS from Snowflake
LIST @SEMANTIC_MODELS;
-- Should show files uploaded from GCS

-- Test 2: Read a file from GCS (if you've uploaded semantic_model.yaml)
-- SELECT $1 FROM @SEMANTIC_MODELS/semantic_model_latest.yaml;

-- Test 3: Create a test table and unload to GCS
CREATE OR REPLACE TABLE TEST_UNLOAD AS 
SELECT 1 as id, 'test' as name;

-- Unload to GCS via stage
COPY INTO @SEMANTIC_MODELS/test_export.csv
FROM TEST_UNLOAD
FILE_FORMAT = (TYPE = 'CSV' HEADER = TRUE);

-- Verify in GCS
LIST @SEMANTIC_MODELS PATTERN = '.*test_export.*';

-- Cleanup
DROP TABLE TEST_UNLOAD;
REMOVE @SEMANTIC_MODELS PATTERN = '.*test_export.*';

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check storage integration
SHOW INTEGRATIONS LIKE 'GCS_INCREMENTALITY_INTEGRATION';

-- Check all stages
SHOW STAGES IN SCHEMA PUBLIC;

-- List files in each stage
LIST @SEMANTIC_MODELS;
LIST @GENERATED_CODE;
LIST @REPORTS;
LIST @ANALYSIS_RESULTS;
LIST @AUDIT_LOGS;

-- ============================================================================
-- NOTES
-- ============================================================================

/*
After running this script:

1. Copy the STORAGE_GCP_SERVICE_ACCOUNT from DESC STORAGE INTEGRATION
2. In GCP, grant that service account access to your bucket:
   
   gcloud storage buckets add-iam-policy-binding gs://incrementality-pipeline-YOUR-PROJECT-ID \
       --member="serviceAccount:PASTE-SERVICE-ACCOUNT-HERE@gcp-project.iam.gserviceaccount.com" \
       --role="roles/storage.objectAdmin"

3. Test by uploading a file to GCS and listing it from Snowflake:
   
   In Python:
   python upload_semantic_model.py
   
   In Snowflake:
   LIST @SEMANTIC_MODELS;

4. Update your .env file with stage paths:
   SEMANTIC_MODEL_STAGE=@SEMANTIC_MODELS/semantic_model_latest.yaml
*/
