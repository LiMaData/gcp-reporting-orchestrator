import os
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

def list_artifacts():
    bucket_name = os.getenv('GCS_BUCKET_NAME')
    project_id = os.getenv('GCP_PROJECT_ID')
    
    if not bucket_name:
        print("Error: GCS_BUCKET_NAME not set")
        return

    client = storage.Client(project=project_id)
    bucket = client.bucket(bucket_name)
    
    print(f"Listing artifacts in: gs://{bucket_name}/\n")
    
    # Show latest files in each folder
    print("📊 LATEST FILES:\n")
    
    folders = {
        'analysis_results/': 'Execution Results',
        'generated_code/': 'Generated Code',
        'reports/': 'Reports'
    }
    
    for folder, label in folders.items():
        print(f"📂 {label} ({folder})")
        blobs = list(bucket.list_blobs(prefix=folder))
        blobs = [b for b in blobs if not b.name.endswith('/') and '.placeholder' not in b.name]
        
        if not blobs:
            print("   (empty)")
        else:
            blobs.sort(key=lambda x: x.time_created, reverse=True)
            for blob in blobs[:3]:
                print(f"   ✓ {blob.name.split('/')[-1]} ({blob.size} bytes)")
        print()
    
    # Show analysis_runs subfolders
    print("📂 Analysis Runs (analysis_runs/)")
    iterator = bucket.list_blobs(prefix='analysis_runs/', delimiter='/')
    list(iterator)
    
    if not iterator.prefixes:
        print("   (no subfolders)")
    else:
        prefixes = sorted(iterator.prefixes, reverse=True)
        for prefix in prefixes:
            print(f"   ✓ {prefix}")

if __name__ == "__main__":
    list_artifacts()
