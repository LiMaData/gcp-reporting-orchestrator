"""
Agent 2: Executor Agent (Snowflake Stored Procedure Version)
Deploys and executes code INSIDE Snowflake for maximum performance
"""

import os
import json
from datetime import datetime
from google.cloud import storage
from snowflake.snowpark import Session
from dotenv import load_dotenv

class ExecutorAgent:
    """
    Executor Agent - Deploys code as Snowflake stored procedure
    """
    
    def __init__(self):
        """Initialize the executor agent"""
        load_dotenv()
        
        # Remove invalid credentials if present
        if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
            cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if cred_path and not os.path.exists(cred_path):
                print(f"Removing invalid GOOGLE_APPLICATION_CREDENTIALS: {cred_path}")
                del os.environ['GOOGLE_APPLICATION_CREDENTIALS']
        
        self.gcs_bucket = os.getenv('GCS_BUCKET_NAME')
        self.gcp_project = os.getenv('GCP_PROJECT_ID', 'gcp-reporting-orchestrator')
        
        # Snowflake connection params
        self.snowflake_params = {
            'account': os.getenv('SNOWFLAKE_ACCOUNT'),
            'user': os.getenv('SNOWFLAKE_USER'),
            'password': os.getenv('SNOWFLAKE_PASSWORD'),
            'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE'),
            'database': os.getenv('SNOWFLAKE_DATABASE'),
            'schema': os.getenv('SNOWFLAKE_SCHEMA'),
            'role': os.getenv('SNOWFLAKE_ROLE')
        }
    
    def execute_as_stored_procedure(self, code, timeout=300):
        """
        Deploy code as Snowflake stored procedure and execute
        
        Args:
            code: Python code to deploy (should have main(session) function)
            timeout: Not used (Snowflake handles timeout)
            
        Returns:
            Dict with execution results
        """
        
        print(f"\n{'='*70}")
        print("EXECUTING CODE AS SNOWFLAKE STORED PROCEDURE")
        print(f"{'='*70}")
        
        session = None
        try:
            # Connect to Snowflake
            print("📡 Connecting to Snowflake...")
            session = Session.builder.configs(self.snowflake_params).create()
            print("✓ Connected to Snowflake")
            print(f"  Database: {self.snowflake_params['database']}")
            print(f"  Schema: {self.snowflake_params['schema']}")
            print(f"  Warehouse: {self.snowflake_params['warehouse']}")
            
            # Create the stored procedure
            print("\n📦 Creating stored procedure...")
            
            proc_name = f"RUN_INCREMENTALITY_ANALYSIS_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # The code should already have a main(session) function
            create_proc_sql = f"""
CREATE OR REPLACE PROCEDURE {proc_name}()
RETURNS VARIANT
LANGUAGE PYTHON
RUNTIME_VERSION = '3.10'
PACKAGES = ('snowflake-snowpark-python', 'scikit-learn', 'scipy', 'numpy', 'pandas', 'statsmodels')
HANDLER = 'main'
AS $$
{code}
$$;
"""
            
            session.sql(create_proc_sql).collect()
            print(f"✓ Stored procedure created: {proc_name}")
            # Execute the stored procedure
            print("\n▶️  Executing analysis in Snowflake...")
            print("   (This may take 1-5 minutes depending on data size)")
            result = session.call(proc_name)
            print("✓ Analysis complete")
            
            # Debug output
            print(f"\n🔍 DEBUG INFO:")
            print(f"   Result type: {type(result)}")
            print(f"   Result preview (first 500 chars): {str(result)[:500]}")
            
            # Parse result
            analysis_results = None
            raw_output = str(result)
            
            if isinstance(result, str):
                try:
                    analysis_results = json.loads(result)
                    print("✓ Successfully parsed JSON result")
                except json.JSONDecodeError as e:
                    print(f"⚠ WARNING: Could not parse result as JSON: {e}")
                    analysis_results = {
                        'status': 'failed',
                        'error': 'Result is not valid JSON',
                        'raw_output': result[:1000]
                    }
            elif isinstance(result, dict):
                analysis_results = result
                raw_output = json.dumps(result, indent=2)
                print("✓ Result is already a dictionary")
            else:
                print(f"⚠ WARNING: Unexpected result type: {type(result)}")
                analysis_results = {
                    'status': 'failed',
                    'error': f'Unexpected result type: {type(result).__name__}',
                    'raw_output': str(result)[:1000]
                }
            
            # Determine success
            success = (isinstance(analysis_results, dict) and 
                      analysis_results.get('status') == 'success')
            
            execution_result = {
                'success': success,
                'returncode': 0 if success else 1,
                'stdout': raw_output,
                'stderr': '' if success else str(analysis_results.get('error', 'Unknown error')),
                'analysis_results': analysis_results,
                'timestamp': datetime.now().isoformat(),
                'execution_location': 'Snowflake',
                'procedure_name': proc_name
            }
            
            # Save results to GCS
            if self.gcs_bucket:
                self._save_results_to_gcs(execution_result)
            
            # Print summary
            print(f"\n{'='*70}")
            print("✓ EXECUTION COMPLETE")
            print(f"{'='*70}")
            print(f"Location: Snowflake (in-database processing)")
            print(f"Procedure: {proc_name}")
            print(f"Status: {'SUCCESS ✓' if success else 'FAILED ✗'}")
            
            if success and analysis_results:
                print("\n📊 RESULTS:")
                print(f"   Treatment Effect: {analysis_results.get('treatment_effect', 'N/A')}")
                print(f"   P-Value: {analysis_results.get('p_value', 'N/A')}")
                print(f"   Confidence Interval: {analysis_results.get('confidence_interval', 'N/A')}")
                print(f"   Matched Pairs: {analysis_results.get('matched_pairs', 'N/A')}")
            elif not success:
                print(f"\n❌ ERROR: {analysis_results.get('error', 'Unknown error')}")
            
            return execution_result
            
        except Exception as e:
            print(f"\n❌ Execution failed: {e}")
            import traceback
            error_trace = traceback.format_exc()
            print(f"\nFull error traceback:")
            print(error_trace)
            
            return {
                'success': False,
                'error': str(e),
                'returncode': -1,
                'stdout': '',
                'stderr': error_trace,
                'analysis_results': None,
                'timestamp': datetime.now().isoformat(),
                'execution_location': 'Snowflake'
            }
            
        finally:
            if session:
                session.close()
                print("\n✓ Snowflake session closed")
    
    def execute_from_gcs(self, gcs_path, timeout=300):
        """
        Load code from GCS and execute as stored procedure
        
        Args:
            gcs_path: GCS path like gs://bucket/path/to/file.py
            timeout: Maximum execution time (not used for stored proc)
            
        Returns:
            Dict with execution results
        """
        
        print(f"\n📥 Loading code from GCS: {gcs_path}")
        
        try:
            # Parse GCS path
            if not gcs_path.startswith('gs://'):
                raise ValueError("GCS path must start with gs://")
            
            parts = gcs_path[5:].split('/', 1)
            bucket_name = parts[0]
            blob_path = parts[1] if len(parts) > 1 else ''
            
            # Download code from GCS
            client = storage.Client(project=self.gcp_project)
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            code = blob.download_as_text()
            
            print(f"✓ Downloaded {len(code)} characters from GCS")
            print(f"   Blob: {blob_path}")
            print(f"   Created: {blob.time_created}")
            
            # Preview code
            print(f"\n📄 Code preview (first 500 chars):")
            print("-" * 70)
            print(code[:500])
            print("...")
            print("-" * 70)
            
            # Execute as stored procedure
            return self.execute_as_stored_procedure(code, timeout)
            
        except Exception as e:
            print(f"\n❌ Failed to load from GCS: {e}")
            import traceback
            error_trace = traceback.format_exc()
            print(error_trace)
            
            return {
                'success': False,
                'error': f'Failed to load from GCS: {e}',
                'returncode': -1,
                'stdout': '',
                'stderr': error_trace,
                'analysis_results': None,
                'timestamp': datetime.now().isoformat()
            }
    
    def _save_results_to_gcs(self, results):
        """Save execution results to GCS"""
        try:
            client = storage.Client(project=self.gcp_project)
            bucket = client.bucket(self.gcs_bucket)
            
            # Save as latest (overwrite)
            blob_path = "analysis_results/latest_execution_result.json"
            blob = bucket.blob(blob_path)
            
            # Save as JSON
            blob.upload_from_string(
                json.dumps(results, indent=2),
                content_type='application/json'
            )
            
            gcs_path = f"gs://{self.gcs_bucket}/{blob_path}"
            print(f"✓ Saved results to GCS: {gcs_path}")
            
        except Exception as e:
            print(f"⚠ WARNING: Failed to save results to GCS: {e}")


# ============================================================================
# MAIN EXECUTION & TESTS
# ============================================================================
if __name__ == "__main__":
    print("\n" + "="*70)
    print("AGENT 2: EXECUTOR AGENT (SNOWFLAKE STORED PROCEDURE)")
    print("="*70)
    
    executor = ExecutorAgent()
    
    # ========================================================================
    # TEST: Execute code from GCS as Snowflake Stored Procedure
    # ========================================================================
    print("\n🧪 TEST: Execute latest generated code from GCS")
    print("="*70)
    
    try:
        client = storage.Client(project=executor.gcp_project)
        bucket = client.bucket(executor.gcs_bucket)
        # Look for the latest fixed file
        blobs = list(bucket.list_blobs(prefix='generated_code/latest_analysis_code.py'))
        
        if blobs:
            latest_blob = blobs[0]
            gcs_path = f"gs://{executor.gcs_bucket}/{latest_blob.name}"
            
            print(f"\n✓ Found latest generated code:")
            print(f"   GCS Path: {gcs_path}")
            print(f"   Created: {latest_blob.time_created}")
            print(f"   Size: {latest_blob.size:,} bytes")
            
            # Execute
            result = executor.execute_from_gcs(gcs_path)
            
            # Final summary
            print(f"\n{'='*70}")
            print("FINAL EXECUTION SUMMARY")
            print(f"{'='*70}")
            print(f"Success: {result['success']}")
            print(f"Return Code: {result['returncode']}")
            print(f"Execution Location: {result.get('execution_location', 'Unknown')}")
            
            if result['success']:
                print(f"\n🎉 ANALYSIS COMPLETED SUCCESSFULLY!")
                if result.get('analysis_results'):
                    print(f"\n📊 Full Results:")
                    print(json.dumps(result['analysis_results'], indent=2))
            else:
                print(f"\n❌ ANALYSIS FAILED")
                if result.get('analysis_results'):
                    print(f"\n📋 Error Details:")
                    print(json.dumps(result['analysis_results'], indent=2))
                elif result.get('stderr'):
                    print(f"\n📋 Error Details:")
                    print(result['stderr'][-2000:])  # Last 2000 chars
                    
        else:
            print("\n❌ No generated code found in GCS (generated_code/latest_analysis_code.py)")
            print("   Run Agent 1 first: python src/agents/analyst_agent.py")
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*70)
    print("✓ Agent 2 execution complete")
    print("="*70)