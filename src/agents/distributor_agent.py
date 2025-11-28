"""
Agent 5: Distributor Agent
Handles the distribution of reports and artifacts to different personas via their preferred channels.
"""

import os
import json
import smtplib
import requests
import shutil
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from datetime import datetime
from google.cloud import storage
from dotenv import load_dotenv

class DistributorAgent:
    """
    Distributor Agent - Orchestrates report delivery
    """
    
    def __init__(self):
        """Initialize the distributor agent"""
        load_dotenv()
        
        self.gcs_bucket = os.getenv('GCS_BUCKET_NAME')
        self.gcp_project = os.getenv('GCP_PROJECT_ID', 'gcp-reporting-orchestrator')
        
        # Configuration
        self.teams_webhook_url = os.getenv('TEAMS_WEBHOOK_URL')
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.office365.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.email_sender = os.getenv('EMAIL_SENDER', self.smtp_user)
        
        # Recipients
        self.recipients = {
            'cmo': os.getenv('CMO_EMAIL'),
            'marketing_ops': os.getenv('MARKETING_OPS_TEAM_CHANNEL'), # This might be a webhook, but keeping for reference
            'data_team': os.getenv('DATA_TEAM_GCS_NOTIFY_EMAIL')
        }

    def distribute_reports(self, all_reports, insights, metadata):
        """
        Main method to distribute reports to all personas
        
        Args:
            all_reports (dict): Output from ReportGeneratorAgent
            insights (dict): Output from InterpreterAgent
            metadata (dict): Additional context (execution results, etc.)
            
        Returns:
            dict: Distribution results
        """
        print(f"\n{'='*80}")
        print("AGENT 5: DISTRIBUTOR - Delivering Reports")
        print(f"{'='*80}")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'channels': {}
        }
        
        # 1. Distribute to CMO (Email)
        if 'cmo' in all_reports:
            print("\n📧 Distributing to CMO (Email)...")
            results['channels']['cmo'] = self._distribute_to_cmo(all_reports['cmo'], insights)
        else:
            print("\n⚠️ [DEBUG] Skipping CMO: 'cmo' key not in all_reports")
            
        # 2. Distribute to Marketing Ops (Teams)
        # FORCE DEBUG: Check if we have the URL
        print(f"\n[DEBUG] TEAMS_WEBHOOK_URL is set: {bool(self.teams_webhook_url)}")
        
        if 'marketing_ops' in all_reports:
            print("\n💬 Distributing to Marketing Ops (Teams)...")
            results['channels']['marketing_ops'] = self._distribute_to_marketing_ops(all_reports['marketing_ops'], insights)
        else:
            print("\n⚠️ [DEBUG] Skipping Marketing Ops: 'marketing_ops' key not in all_reports")
            print(f"Keys available: {list(all_reports.keys())}")
            
        # 3. Distribute to Data Team (GCS Artifacts)
        print("\n💾 Distributing to Data Team (GCS Artifacts)...")
        results['channels']['data_team'] = self._distribute_to_data_team(all_reports, insights, metadata)
        
        return results

    def _distribute_to_cmo(self, report, insights):
        """Send email with PDF attachment to CMO (or save locally in demo mode)"""
        recipient = self.recipients['cmo']
        
        # Check if we should use Demo Mode (missing creds OR placeholder creds)
        is_placeholder = self.smtp_user and ('your.' in self.smtp_user or 'example.com' in self.smtp_user)
        if not self.smtp_user or not self.smtp_password or is_placeholder:
            print("  [INFO] SMTP credentials missing or are placeholders. Switching to Local Demo Mode.")
            return self._save_to_local_inbox('CMO_Inbox', report, insights, 'email')
            
        if not recipient:
            print("  [SKIP] No CMO email configured (CMO_EMAIL)")
            return {'status': 'skipped', 'reason': 'no_recipient'}
            
        if 'gcs_path' not in report:
            print("  [SKIP] No PDF report available for CMO")
            return {'status': 'skipped', 'reason': 'no_pdf'}
            
        # ... (rest of real email logic) ...
        # Download PDF from GCS to attach
        local_pdf_path = self._download_from_gcs(report['gcs_path'])
        if not local_pdf_path:
            return {'status': 'failed', 'reason': 'download_failed'}
            
        subject = f"Incrementality Analysis Results - {datetime.now().strftime('%Y-%m-%d')}"
        
        body = f"""
        Dear CMO,
        
        Please find attached the latest Incrementality Analysis Report.
        
        Executive Summary:
        {insights.get('summary', 'Analysis completed successfully.')}
        
        Key Metrics:
        - Treatment Effect: {insights.get('treatment_effect', 0):.2%}
        - Significance: {'Yes' if insights.get('is_significant') else 'No'}
        
        Best regards,
        GCP Reporting Orchestrator
        """
        
        try:
            self._send_email(recipient, subject, body, attachments=[local_pdf_path])
            print(f"  [OK] Email sent to {recipient}")
            
            # Clean up temp file
            if os.path.exists(local_pdf_path):
                os.remove(local_pdf_path)
                
            return {'status': 'success', 'recipient': recipient}
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  [ERROR] Failed to send email: {e}")
            return {'status': 'failed', 'error': str(e)}

    def _distribute_to_marketing_ops(self, report, insights):
        """Send Teams message to Marketing Ops (or save locally in demo mode)"""
        # Check if we should use Demo Mode
        is_placeholder = self.teams_webhook_url and ('webhook/...' in self.teams_webhook_url)
        if not self.teams_webhook_url or is_placeholder:
            print("  [INFO] Teams webhook missing or is placeholder. Switching to Local Demo Mode.")
            return self._save_to_local_inbox('MarketingOps_Channel', report, insights, 'teams')
            
        # ... (rest of real Teams logic) ...
        # Create Robust Text-Based Message (Adaptive Cards can be flaky)
        lift = insights.get('incremental_lift_pct', 0)
        is_significant = insights.get('is_significant', False)
        significance_icon = "✅" if is_significant else "⚠️"
        significance_text = "Significant" if is_significant else "Not Significant"
        confidence = insights.get('confidence_level', '95%')
        summary = insights.get('summary', 'Analysis completed successfully.')
        
        # Convert gs:// path to clickable HTTPS URL
        gcs_path = report.get('gcs_path', '')
        if gcs_path.startswith('gs://'):
            # Format: gs://bucket/path/to/file -> https://console.cloud.google.com/storage/browser/_details/bucket/path/to/file
            path_parts = gcs_path.replace('gs://', '').split('/', 1)
            if len(path_parts) == 2:
                bucket, blob = path_parts
                report_url = f"https://console.cloud.google.com/storage/browser/_details/{bucket}/{blob}"
            else:
                report_url = 'https://console.cloud.google.com/storage'
        else:
            report_url = 'https://console.cloud.google.com/storage'
        
        # Format as Markdown for Teams
        text_message = f"""
### 📊 Incrementality Analysis Results

**Marketing Ops Report** - {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

*   **Incremental Lift:** {lift:.2f}%
*   **Significance:** {significance_icon} {significance_text}
*   **Confidence:** {confidence}

**Executive Summary:**
{summary}

[View Full Report PDF]({report_url})
"""
        
        # Use the simplest payload format that always works
        message = {
            "text": text_message
        }
        
        try:
            print(f"  [DEBUG] Sending text message to Teams: {text_message[:100]}...")
            response = requests.post(self.teams_webhook_url, json=message, timeout=10)
            
            if response.status_code in [200, 202]:
                print("  [OK] Teams notification sent")
                return {'status': 'success'}
            else:
                print(f"  [ERROR] Teams API returned {response.status_code}: {response.text}")
                return {'status': 'failed', 'error': f'HTTP {response.status_code}'}
        except Exception as e:
            print(f"  [ERROR] Failed to send Teams message: {e}")
            return {'status': 'failed', 'error': str(e)}

    def _save_to_local_inbox(self, folder_name, report, insights, channel_type):
        """Simulate delivery by saving to a local folder"""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        inbox_dir = os.path.join(base_dir, 'output', 'distribution', folder_name)
        os.makedirs(inbox_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        print(f"  [DEMO] Saving to local inbox: {inbox_dir}")
        
        if channel_type == 'email':
            # Simulate Email: Save PDF and a text file for the body
            if 'gcs_path' in report:
                local_pdf = self._download_from_gcs(report['gcs_path'])
                if local_pdf:
                    shutil.copy(local_pdf, os.path.join(inbox_dir, f"Report_{timestamp}.pdf"))
                    os.remove(local_pdf)
            
            with open(os.path.join(inbox_dir, f"Email_Body_{timestamp}.txt"), 'w') as f:
                f.write(f"Subject: Incrementality Analysis Results\n")
                f.write(f"To: CMO\n\n")
                f.write(f"Executive Summary:\n{insights.get('summary', 'N/A')}\n")
                
        elif channel_type == 'teams':
            # Simulate Teams: Save a text file formatted like a chat message
            with open(os.path.join(inbox_dir, f"Teams_Message_{timestamp}.txt"), 'w', encoding='utf-8') as f:
                f.write("🤖 [BOT] posted in Marketing Ops:\n\n")
                f.write("📊 Incrementality Analysis Complete\n")
                f.write(f"----------------------------------------\n")
                f.write(f"📈 Incremental Lift: {insights.get('incremental_lift_pct', 0):.2f}%\n")
                f.write(f"🎯 Significant: {'✅ Yes' if insights.get('is_significant') else '⚠️ No'}\n")
                f.write(f"🔗 Link to Report: {report.get('gcs_path', 'N/A')}\n")
                
        return {'status': 'success', 'mode': 'demo_local', 'path': inbox_dir}

    def _distribute_to_data_team(self, all_reports, insights, metadata):
        """Organize all artifacts in GCS for the Data Team"""
        if not self.gcs_bucket:
            print("  [SKIP] No GCS bucket configured")
            return {'status': 'skipped', 'reason': 'no_bucket'}
            
        run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_path = f"analysis_runs/{run_id}"
        
        print(f"  Organizing artifacts in: gs://{self.gcs_bucket}/{base_path}/")
        
        artifacts_log = []
        
        try:
            client = storage.Client(project=self.gcp_project)
            bucket = client.bucket(self.gcs_bucket)
            
            # 1. Save Insights JSON
            blob = bucket.blob(f"{base_path}/results/insights.json")
            blob.upload_from_string(json.dumps(insights, indent=2), content_type='application/json')
            artifacts_log.append("results/insights.json")
            
            # 2. Save Metadata/Context
            blob = bucket.blob(f"{base_path}/results/metadata.json")
            # Filter out non-serializable objects if any
            safe_metadata = {k: str(v) for k, v in metadata.items() if isinstance(v, (str, int, float, bool, dict, list))}
            blob.upload_from_string(json.dumps(safe_metadata, indent=2), content_type='application/json')
            artifacts_log.append("results/metadata.json")
            
            # 3. Copy Reports
            for persona, report in all_reports.items():
                if 'gcs_path' in report:
                    source_blob_name = report['gcs_path'].replace(f"gs://{self.gcs_bucket}/", "")
                    source_blob = bucket.blob(source_blob_name)
                    
                    if source_blob.exists():
                        dest_blob_name = f"{base_path}/reports/{persona}_report.pdf"
                        bucket.copy_blob(source_blob, bucket, dest_blob_name)
                        artifacts_log.append(f"reports/{persona}_report.pdf")
            
            # 4. Copy Python Script (from generated_code/)
            if 'analyst_result' in metadata and 'gcs_path' in metadata['analyst_result']:
                script_gcs_path = metadata['analyst_result']['gcs_path']
                source_blob_name = script_gcs_path.replace(f"gs://{self.gcs_bucket}/", "")
                source_blob = bucket.blob(source_blob_name)
                
                if source_blob.exists():
                    dest_blob_name = f"{base_path}/code/analysis_script.py"
                    bucket.copy_blob(source_blob, bucket, dest_blob_name)
                    artifacts_log.append(f"code/analysis_script.py")
                    print(f"  [OK] Copied Python script to analysis_runs")
            
            print(f"  [OK] Archived {len(artifacts_log)} artifacts")
            
            # 4. Send Notification Email to Data Team (if configured)
            data_team_email = self.recipients['data_team']
            if data_team_email:
                print(f"  Sending notification to Data Team: {data_team_email}")
                
                subject = f"Data Team: Analysis Run {run_id} Artifacts"
                body = f"""
                Hello Data Team,
                
                A new analysis run has completed.
                
                GCS Location: gs://{self.gcs_bucket}/{base_path}/
                
                Attached:
                1. Analysis Script (Python code as .txt file - rename to .py to use)
                2. Data Team Report (PDF)
                
                Artifacts archived:
                {chr(10).join(['- ' + a for a in artifacts_log])}
                
                Regards,
                GCP Reporting Orchestrator
                """
                
                attachments = []
                
                # Find script and report to attach
                # We need to download them locally first if we want to attach them
                # For the script, we look in metadata or all_reports
                # This is a bit tricky since we just uploaded them to GCS.
                # But we can try to find the local temp files or re-download.
                
                # Let's try to attach the PDF report if available
                if 'data_team' in all_reports and 'gcs_path' in all_reports['data_team']:
                     local_report = self._download_from_gcs(all_reports['data_team']['gcs_path'])
                     if local_report:
                         attachments.append(local_report)
                         
                
                # Attach the Python script from the ORIGINAL location (more reliable)
                # Download from generated_code/latest_analysis_code.py
                if 'analyst_result' in metadata and 'gcs_path' in metadata['analyst_result']:
                    script_gcs_path = metadata['analyst_result']['gcs_path']
                    print(f"  [DEBUG] Downloading script from original location: {script_gcs_path}")
                    local_script = self._download_from_gcs(script_gcs_path)
                    if local_script:
                        print(f"  [DEBUG] Script downloaded to: {local_script}")
                        
                        # Rename .py to .txt to bypass corporate email filters
                        if local_script.endswith('.py'):
                            txt_path = local_script.replace('.py', '.txt')
                            os.rename(local_script, txt_path)
                            local_script = txt_path
                            print(f"  [DEBUG] Renamed to .txt for email compatibility: {local_script}")
                        
                        attachments.append(local_script)
                    else:
                        print(f"  [WARNING] Failed to download script from {script_gcs_path}")
                else:
                    print(f"  [WARNING] No analyst_result in metadata, cannot attach script")
                
                
                try:
                    print(f"  [INFO] Attempting to send email to {data_team_email}...")
                    print(f"  [INFO] Attachments: {[os.path.basename(a) for a in attachments]}")
                    self._send_email(data_team_email, subject, body, attachments)
                    print(f"  [OK] Notification sent successfully to {data_team_email}")
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    print(f"  [ERROR] Failed to send Data Team email: {e}")
                
                # Cleanup temp files
                for f in attachments:
                    if os.path.exists(f):
                        os.remove(f)

            return {'status': 'success', 'path': f"gs://{self.gcs_bucket}/{base_path}", 'artifacts': artifacts_log}
            
        except Exception as e:
            print(f"  [ERROR] Failed to organize artifacts: {e}")
            return {'status': 'failed', 'error': str(e)}

    def _download_from_gcs(self, gcs_path):
        """Helper to download file from GCS to local temp"""
        try:
            if not gcs_path.startswith('gs://'):
                return None
                
            parts = gcs_path[5:].split('/', 1)
            bucket_name = parts[0]
            blob_path = parts[1]
            
            client = storage.Client(project=self.gcp_project)
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            
            filename = os.path.basename(blob_path)
            local_path = os.path.join(os.getcwd(), 'tmp', filename)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            blob.download_to_filename(local_path)
            return local_path
        except Exception as e:
            print(f"  [ERROR] GCS download failed: {e}")
            return None

    def _send_email(self, to_email, subject, body, attachments=None):
        """Send email via SMTP"""
        if not self.smtp_user or not self.smtp_password:
            print("  [MOCK] Email credentials missing. Printing email content:")
            print(f"    To: {to_email}")
            print(f"    Subject: {subject}")
            print("    [Email body suppressed]")
            return

        msg = MIMEMultipart()
        msg['From'] = self.email_sender
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Sanitize body to avoid encoding issues
        try:
            body = body.encode('ascii', 'ignore').decode('ascii')
        except:
            pass
            
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        if attachments:
            for f in attachments:
                with open(f, "rb") as fil:
                    part = MIMEApplication(fil.read(), Name=os.path.basename(f))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(f)}"'
                msg.attach(part)
        
        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)

if __name__ == "__main__":
    # Test the agent
    agent = DistributorAgent()
    print("Distributor Agent initialized.")
