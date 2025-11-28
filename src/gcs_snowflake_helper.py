"""
Helper library for GCS and Snowflake integration
Used by Cloud Functions and agents
"""

from google.cloud import storage
import snowflake.connector
import yaml
import json
from datetime import datetime, timedelta
import os

class GCSSnowflakeHelper:
    """Helper class for GCS and Snowflake operations"""
    
    def __init__(self, 
                 project_id: str = None,
                 bucket_name: str = None,
                 snowflake_account: str = None,
                 snowflake_user: str = None,
                 snowflake_password: str = None,
                 snowflake_warehouse: str = None,
                 snowflake_database: str = None,
                 snowflake_schema: str = None,
                 snowflake_role: str = None):
        
        # Load from environment if not provided
        self.project_id = project_id or os.getenv('GCP_PROJECT_ID')
        self.bucket_name = bucket_name or os.getenv('GCS_BUCKET_NAME')
        
        # Initialize GCS client
        self.storage_client = storage.Client(project=self.project_id)
        self.bucket = self.storage_client.bucket(self.bucket_name)
        
        # Snowflake connection (optional)
        self.snowflake_conn = None
        if snowflake_account or os.getenv('SNOWFLAKE_ACCOUNT'):
            self.snowflake_conn = snowflake.connector.connect(
                user=snowflake_user or os.getenv('SNOWFLAKE_USER'),
                password=snowflake_password or os.getenv('SNOWFLAKE_PASSWORD'),
                account=snowflake_account or os.getenv('SNOWFLAKE_ACCOUNT'),
                warehouse=snowflake_warehouse or os.getenv('SNOWFLAKE_WAREHOUSE'),
                database=snowflake_database or os.getenv('SNOWFLAKE_DATABASE'),
                schema=snowflake_schema or os.getenv('SNOWFLAKE_SCHEMA'),
                role=snowflake_role or os.getenv('SNOWFLAKE_ROLE')
            )
    
    # ========================================================================
    # SEMANTIC MODELS
    # ========================================================================
    
    def upload_semantic_model(self, file_path: str) -> dict:
        """Upload semantic model to GCS"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        blob_name = f"semantic_models/semantic_model_v{timestamp}.yaml"
        
        blob = self.bucket.blob(blob_name)
        blob.upload_from_filename(file_path)
        
        # Also upload as latest
        latest_blob = self.bucket.blob("semantic_models/semantic_model_latest.yaml")
        latest_blob.upload_from_filename(file_path)
        
        print(f"Uploaded semantic model to GCS")
        print(f"  Versioned: gs://{self.bucket_name}/{blob_name}")
        print(f"  Latest: gs://{self.bucket_name}/semantic_models/semantic_model_latest.yaml")
        
        return {
            'version': timestamp,
            'gcs_path': f'gs://{self.bucket_name}/{blob_name}',
            'snowflake_path': f'@SEMANTIC_MODELS/{blob_name.split("/")[-1]}'
        }
    
    def download_semantic_model(self, version: str = 'latest') -> dict:
        """Download semantic model from GCS"""
        
        blob_name = f"semantic_models/semantic_model_{version}.yaml"
        blob = self.bucket.blob(blob_name)
        
        if not blob.exists():
            raise FileNotFoundError(f"Semantic model version '{version}' not found in GCS")
        
        content = blob.download_as_text()
        return yaml.safe_load(content)
    
    # ========================================================================
    # GENERATED CODE
    # ========================================================================
    
    def save_generated_code(self, code: str, run_id: str, agent_name: str) -> dict:
        """Save generated Python code to GCS"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        blob_name = f"generated_code/{run_id}/{agent_name}_{timestamp}.py"
        
        blob = self.bucket.blob(blob_name)
        blob.upload_from_string(code, content_type='text/x-python')
        
        blob.metadata = {
            'run_id': run_id,
            'agent': agent_name,
            'timestamp': timestamp
        }
        blob.patch()
        
        print(f"Saved generated code to GCS: gs://{self.bucket_name}/{blob_name}")
        
        return {
            'run_id': run_id,
            'gcs_path': f'gs://{self.bucket_name}/{blob_name}',
            'snowflake_path': f'@GENERATED_CODE/{run_id}/{agent_name}_{timestamp}.py'
        }
    
    def load_generated_code(self, run_id: str, agent_name: str) -> str:
        """Load generated code from GCS"""
        
        # Find the latest file for this run_id and agent
        prefix = f"generated_code/{run_id}/{agent_name}_"
        blobs = list(self.bucket.list_blobs(prefix=prefix))
        
        if not blobs:
            raise FileNotFoundError(f"No generated code found for run_id={run_id}, agent={agent_name}")
        
        # Get the most recent
        latest_blob = max(blobs, key=lambda b: b.updated)
        return latest_blob.download_as_text()
    
    # ========================================================================
    # REPORTS
    # ========================================================================
    
    def save_report(self, content: str, run_id: str, persona: str, format: str = 'html') -> dict:
        """Save generated report to GCS"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        blob_name = f"reports/{run_id}/{persona}_report_{timestamp}.{format}"
        
        blob = self.bucket.blob(blob_name)
        blob.upload_from_string(content)
        
        blob.metadata = {
            'run_id': run_id,
            'persona': persona,
            'timestamp': timestamp,
            'format': format
        }
        blob.patch()
        
        # Generate signed URL for distribution (valid for 7 days)
        url = blob.generate_signed_url(
            version='v4',
            expiration=timedelta(days=7),
            method='GET'
        )
        
        print(f"Saved report to GCS: gs://{self.bucket_name}/{blob_name}")
        print(f"Public URL (valid 7 days): {url}")
        
        return {
            'run_id': run_id,
            'persona': persona,
            'gcs_path': f'gs://{self.bucket_name}/{blob_name}',
            'public_url': url,
            'snowflake_path': f'@REPORTS/{run_id}/{persona}_report_{timestamp}.{format}'
        }
    
    # ========================================================================
    # SNOWFLAKE OPERATIONS
    # ========================================================================
    
    def list_stage_files(self, stage_name: str) -> list:
        """List files in a Snowflake stage"""
        
        if not self.snowflake_conn:
            raise Exception("Snowflake connection not configured")
        
        cursor = self.snowflake_conn.cursor()
        cursor.execute(f"LIST @{stage_name}")
        
        files = []
        for row in cursor:
            files.append({
                'name': row[0],
                'size': row[1],
                'md5': row[2],
                'last_modified': row[3]
            })
        
        cursor.close()
        return files
    
    def verify_gcs_snowflake_sync(self, stage_name: str, gcs_prefix: str) -> dict:
        """Verify files are accessible from both GCS and Snowflake"""
        
        # Get files from GCS
        gcs_files = set()
        blobs = self.bucket.list_blobs(prefix=gcs_prefix)
        for blob in blobs:
            filename = blob.name.split('/')[-1]
            if filename and filename != '.placeholder':
                gcs_files.add(filename)
        
        # Get files from Snowflake stage
        sf_files = set()
        try:
            stage_files = self.list_stage_files(stage_name)
            for f in stage_files:
                filename = f['name'].split('/')[-1]
                if filename:
                    sf_files.add(filename)
        except Exception as e:
            print(f"Warning: Could not list Snowflake stage: {e}")
            sf_files = set()
        
        return {
            'gcs_count': len(gcs_files),
            'snowflake_count': len(sf_files),
            'in_sync': gcs_files == sf_files,
            'only_in_gcs': list(gcs_files - sf_files),
            'only_in_snowflake': list(sf_files - gcs_files)
        }
    
    def close(self):
        """Close Snowflake connection"""
        if self.snowflake_conn:
            self.snowflake_conn.close()

# Example usage
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    # Initialize helper
    helper = GCSSnowflakeHelper()
    
    print(f"Project ID: {helper.project_id}")
    print(f"Bucket: {helper.bucket_name}")
    
    # Test: Upload semantic model
    semantic_model_path = "docs/semantic_model.yaml"
    if os.path.exists(semantic_model_path):
        result = helper.upload_semantic_model(semantic_model_path)
        print(f"\nUploaded: {result['gcs_path']}")
    
    # Test: Download semantic model
    try:
        model = helper.download_semantic_model()
        print(f"\nDownloaded semantic model")
        print(f"Table: {model.get('table', {}).get('name', 'N/A')}")
    except Exception as e:
        print(f"\nCould not download: {e}")
    
    # Close connection
    helper.close()
