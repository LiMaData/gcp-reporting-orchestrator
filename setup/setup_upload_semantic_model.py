#!/usr/bin/env python3
"""
Upload semantic model to GCS bucket that Snowflake can access
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.cloud import storage
from dotenv import load_dotenv
from datetime import datetime

def main():
    load_dotenv()
    
    # Get configuration from environment
    project_id = os.getenv('GCP_PROJECT_ID', 'gcp-reporting-orchestrator')
    bucket_name = os.getenv('GCS_BUCKET_NAME', 'incrementality-pipeline-gcp-reporting-orchestrator')
    
    print("=" * 60)
    print("Semantic Model Upload Tool")
    print("=" * 60)
    print(f"Project: {project_id}")
    print(f"Bucket: {bucket_name}")
    print()
    
    # Path to semantic model (use the updated v2)
    semantic_model_path = "semantic_model_mvp_v2.yaml"
    
    # Try alternative paths if not found
    if not os.path.exists(semantic_model_path):
        alternative_paths = [
            "docs/semantic_model.yaml",
            "semantic_model.yaml",
            "docs/semantic_model_mvp_v2.yaml"
        ]
        
        for alt_path in alternative_paths:
            if os.path.exists(alt_path):
                semantic_model_path = alt_path
                break
        else:
            print(f"❌ Error: Semantic model not found")
            print(f"Tried:")
            print(f"  - semantic_model_mvp_v2.yaml")
            for path in alternative_paths:
                print(f"  - {path}")
            return 1
    
    print(f" Found semantic model: {semantic_model_path}")
    print()
    
    # Initialize GCS client
    try:
        client = storage.Client(project=project_id)
        bucket = client.bucket(bucket_name)
        print("✓ Connected to GCS")
    except Exception as e:
        print(f" Failed to connect to GCS: {e}")
        return 1
    
    # Upload as semantic_model.yaml (main file, no "latest" suffix)
    print(f"Uploading to GCS...")
    try:
        # Main file: semantic_model.yaml
        blob_main = bucket.blob('semantic_models/semantic_model.yaml')
        with open(semantic_model_path, 'rb') as f:
            blob_main.upload_from_file(f, content_type='application/x-yaml')
        gcs_main_path = f"gs://{bucket_name}/semantic_models/semantic_model.yaml"
        print(f"✓ Uploaded: {gcs_main_path}")
        
        # Also save versioned backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        blob_versioned = bucket.blob(f'semantic_models/semantic_model_v{timestamp}.yaml')
        with open(semantic_model_path, 'rb') as f:
            blob_versioned.upload_from_file(f, content_type='application/x-yaml')
        gcs_versioned_path = f"gs://{bucket_name}/semantic_models/semantic_model_v{timestamp}.yaml"
        print(f"✓ Archived: {gcs_versioned_path}")
        
    except Exception as e:
        print(f" Upload failed: {e}")
        return 1
    
    # Success summary
    print()
    print("=" * 60)
    print("✓ Upload Complete!")
    print("=" * 60)
    print(f"Main file:    {gcs_main_path}")
    print(f"Backup copy:  {gcs_versioned_path}")
    print(f"Version:      {timestamp}")
    print()
    print("Snowflake stage path:")
    print(f"  @PLAYGROUND_LM.GCP_REPORTING_ORCHESTRATOR.SEMANTIC_MODELS/semantic_model.yaml")
    print()
    print("To verify in Snowflake, run:")
    print("  USE SCHEMA PLAYGROUND_LM.GCP_REPORTING_ORCHESTRATOR;")
    print("  LIST @SEMANTIC_MODELS;")
    print("  SELECT $1 FROM @SEMANTIC_MODELS/semantic_model.yaml;")
    print()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())