#!/usr/bin/env python3
"""
Automated Snowflake External Stages Setup
No UI required - runs everything via Python
"""

import snowflake.connector
import os
from dotenv import load_dotenv
import sys

def setup_snowflake_stages(gcp_project_id: str, bucket_name: str):
    """
    Automate Snowflake storage integration and external stages setup
    
    Args:
        gcp_project_id: Your GCP project ID
        bucket_name: Your GCS bucket name
    """
    
    load_dotenv()
    
    print("=" * 70)
    print("Snowflake External Stages Setup (Automated)")
    print("=" * 70)
    print()
    
    # Connect to Snowflake
    print("Connecting to Snowflake...")
    try:
        conn = snowflake.connector.connect(
            user=os.getenv('SNOWFLAKE_USER'),
            password=os.getenv('SNOWFLAKE_PASSWORD'),
            account=os.getenv('SNOWFLAKE_ACCOUNT'),
            warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
            database=os.getenv('SNOWFLAKE_DATABASE'),
            schema=os.getenv('SNOWFLAKE_SCHEMA'),
            role=os.getenv('SNOWFLAKE_ROLE')
        )
        print("OK Connected to Snowflake")
        print()
    except Exception as e:
        print(f"ERROR Connection failed: {e}")
        return False
    
    cursor = conn.cursor()
    
    # Step 1: Create Storage Integration (requires ACCOUNTADMIN)
    print("Step 1: Creating Storage Integration")
    print("Note: This requires ACCOUNTADMIN role")
    print()
    
    try:
        # Switch to ACCOUNTADMIN
        cursor.execute("USE ROLE ACCOUNTADMIN")
        print("OK Switched to ACCOUNTADMIN role")
        
        # Create storage integration
        storage_integration_sql = f"""
        CREATE OR REPLACE STORAGE INTEGRATION GCS_INCREMENTALITY_INTEGRATION
            TYPE = EXTERNAL_STAGE
            STORAGE_PROVIDER = 'GCS'
            ENABLED = TRUE
            STORAGE_ALLOWED_LOCATIONS = ('gcs://{bucket_name}/')
            COMMENT = 'Integration for incrementality analysis pipeline with GCS'
        """
        
        cursor.execute(storage_integration_sql)
        print("OK Storage integration created: GCS_INCREMENTALITY_INTEGRATION")
        
        # Grant usage to SYSADMIN
        cursor.execute("GRANT USAGE ON INTEGRATION GCS_INCREMENTALITY_INTEGRATION TO ROLE SYSADMIN")
        print("OK Granted usage to SYSADMIN role")
        print()
        
        # Get the Snowflake service account
        print("IMPORTANT: Copy this service account for GCP setup")
        print("-" * 70)
        cursor.execute("DESC STORAGE INTEGRATION GCS_INCREMENTALITY_INTEGRATION")
        
        for row in cursor:
            if row[0] == 'STORAGE_GCP_SERVICE_ACCOUNT':
                snowflake_sa = row[1]
                print(f"Snowflake Service Account: {snowflake_sa}")
                print()
                print("Run this command in your terminal to grant access:")
                print(f'gcloud storage buckets add-iam-policy-binding gs://{bucket_name} \\')
                print(f'    --member="serviceAccount:{snowflake_sa}" \\')
                print(f'    --role="roles/storage.objectAdmin"')
                print("-" * 70)
                print()
                
                # Save to file for easy access
                with open("snowflake_service_account.txt", "w") as f:
                    f.write(f"Snowflake Service Account:\n{snowflake_sa}\n\n")
                    f.write(f"GCP Command:\n")
                    f.write(f'gcloud storage buckets add-iam-policy-binding gs://{bucket_name} \\\n')
                    f.write(f'    --member="serviceAccount:{snowflake_sa}" \\\n')
                    f.write(f'    --role="roles/storage.objectAdmin"\n')
                
                print("OK Service account info saved to: snowflake_service_account.txt")
                print()
                
                # Prompt user to grant access
                input("Press Enter after you've run the GCP command above...")
        
    except Exception as e:
        if "Insufficient privileges" in str(e):
            print("ERROR ACCOUNTADMIN role required for storage integration")
            print("  Please ask your Snowflake admin to run setup_snowflake_stages.sql")
            print("  Or grant ACCOUNTADMIN temporarily")
            cursor.close()
            conn.close()
            return False
        else:
            print(f"ERROR Error creating storage integration: {e}")
            cursor.close()
            conn.close()
            return False
    
    # Step 2: Create External Stages
    print()
    print("Step 2: Creating External Stages")
    print()
    
    try:
        # Switch to SYSADMIN
        cursor.execute("USE ROLE SYSADMIN")
        cursor.execute(f"USE WAREHOUSE {os.getenv('SNOWFLAKE_WAREHOUSE')}")
        cursor.execute(f"USE DATABASE {os.getenv('SNOWFLAKE_DATABASE')}")
        
        # CLEANUP: Drop stages from PUBLIC schema if they exist
        print("Cleaning up old stages in PUBLIC schema...")
        try:
            cursor.execute("USE SCHEMA PUBLIC")
            stages_to_drop = ['SEMANTIC_MODELS', 'GENERATED_CODE', 'REPORTS', 'ANALYSIS_RESULTS', 'AUDIT_LOGS']
            for stage in stages_to_drop:
                cursor.execute(f"DROP STAGE IF EXISTS {stage}")
                print(f"OK Dropped stage from PUBLIC: {stage}")
        except Exception as e:
            print(f"WARNING Cleanup failed (ignoring): {e}")

        # Switch to correct schema
        target_schema = "GCP_REPORTING_ORCHESTRATOR"
        print(f"\nSwitching to schema: {target_schema}")
        cursor.execute(f"USE SCHEMA {target_schema}")
        
        # Create external stages
        stages = [
            {
                'name': 'SEMANTIC_MODELS',
                'url': f'gcs://{bucket_name}/semantic_models/',
                'comment': 'External stage for semantic models (YAML/JSON) in GCS'
            },
            {
                'name': 'GENERATED_CODE',
                'url': f'gcs://{bucket_name}/generated_code/',
                'comment': 'External stage for generated Python code in GCS'
            },
            {
                'name': 'REPORTS',
                'url': f'gcs://{bucket_name}/reports/',
                'comment': 'External stage for generated reports in GCS'
            }
        ]
        
        for stage in stages:
            stage_sql = f"""
            CREATE OR REPLACE STAGE {stage['name']}
                URL = '{stage['url']}'
                STORAGE_INTEGRATION = GCS_INCREMENTALITY_INTEGRATION
                DIRECTORY = (ENABLE = TRUE)
                FILE_FORMAT = (TYPE = 'CSV')
                COMMENT = '{stage['comment']}'
            """
            cursor.execute(stage_sql)
            print(f"OK Created external stage: {stage['name']}")
        
        # Create internal stages
        internal_stages = [
            {
                'name': 'ANALYSIS_RESULTS',
                'comment': 'Internal stage for analysis results'
            },
            {
                'name': 'AUDIT_LOGS',
                'comment': 'Internal stage for audit logs'
            }
        ]
        
        for stage in internal_stages:
            stage_sql = f"""
            CREATE OR REPLACE STAGE {stage['name']}
                DIRECTORY = (ENABLE = TRUE)
                COMMENT = '{stage['comment']}'
            """
            cursor.execute(stage_sql)
            print(f"OK Created internal stage: {stage['name']}")
        
        print()
        print("OK All stages created successfully")
        
    except Exception as e:
        print(f"ERROR Error creating stages: {e}")
        cursor.close()
        conn.close()
        return False
    
    # Step 3: Verify stages
    print()
    print("Step 3: Verifying Stages")
    print()
    
    try:
        cursor.execute("SHOW STAGES IN SCHEMA GCP_REPORTING_ORCHESTRATOR")
        print("Available stages:")
        for row in cursor:
            print(f"  - {row[1]}")  # Stage name is in column 1
        
    except Exception as e:
        print(f"Warning: Could not list stages: {e}")
    
    # Step 4: Test external stage access
    print()
    print("Step 4: Testing External Stage Access")
    print()
    
    try:
        cursor.execute("LIST @SEMANTIC_MODELS")
        files = cursor.fetchall()
        
        if files:
            print(f"OK Found {len(files)} file(s) in @SEMANTIC_MODELS:")
            for file in files[:5]:  # Show first 5
                print(f"  - {file[0]}")
        else:
            print("WARNING No files found in @SEMANTIC_MODELS (this is OK if you haven't uploaded yet)")
        
    except Exception as e:
        print(f"WARNING Could not list files: {e}")
        print("  This might be because:")
        print("  1. GCP permissions not granted yet")
        print("  2. No files uploaded to GCS yet")
    
    # Cleanup
    cursor.close()
    conn.close()
    
    # Summary
    print()
    print("=" * 70)
    print("Setup Complete!")
    print("=" * 70)
    print()
    print("Next Steps:")
    print("  1. OK Storage integration created")
    print("  2. OK External stages created")
    print("  3. -> Upload semantic model: python upload_semantic_model.py")
    print("  4. -> Verify: LIST @SEMANTIC_MODELS; in Snowflake")
    print()
    
    return True


def main():
    """Main entry point"""
    
    load_dotenv()
    
    # Get GCP configuration
    gcp_project_id = os.getenv('GCP_PROJECT_ID')
    bucket_name = os.getenv('GCS_BUCKET_NAME')
    
    if not gcp_project_id or not bucket_name:
        print("Error: GCP configuration not found in .env")
        print("Please run setup_gcp.ps1 first")
        return 1
    
    print(f"GCP Project: {gcp_project_id}")
    print(f"GCS Bucket: {bucket_name}")
    print()
    
    # Confirm
    confirm = input("Proceed with Snowflake setup? (y/n): ")
    if confirm.lower() != 'y':
        print("Setup cancelled")
        return 0
    
    print()
    
    # Run setup
    success = setup_snowflake_stages(gcp_project_id, bucket_name)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
