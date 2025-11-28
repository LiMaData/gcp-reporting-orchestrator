"""
Test Distributor Agent
"""

import unittest
from unittest.mock import MagicMock, patch
import os
import sys
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.distributor_agent import DistributorAgent

class TestDistributorAgent(unittest.TestCase):
    
    def setUp(self):
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'GCS_BUCKET_NAME': 'test-bucket',
            'GCP_PROJECT_ID': 'test-project',
            'TEAMS_WEBHOOK_URL': 'https://test-webhook',
            'SMTP_SERVER': 'smtp.test.com',
            'SMTP_USERNAME': 'user',
            'SMTP_PASSWORD': 'password',
            'CMO_EMAIL': 'cmo@test.com',
            'MARKETING_OPS_TEAM_CHANNEL': 'marketing-ops',
            'DATA_TEAM_GCS_NOTIFY_EMAIL': 'data@test.com'
        })
        self.env_patcher.start()
        
        self.agent = DistributorAgent()
        
    def tearDown(self):
        self.env_patcher.stop()
        
    @patch('src.agents.distributor_agent.smtplib.SMTP')
    @patch('src.agents.distributor_agent.DistributorAgent._download_from_gcs')
    def test_distribute_to_cmo(self, mock_download, mock_smtp):
        # Setup mocks
        mock_download.return_value = 'tmp/test_report.pdf'
        
        # Create dummy file for attachment
        os.makedirs('tmp', exist_ok=True)
        with open('tmp/test_report.pdf', 'w') as f:
            f.write('dummy pdf content')
            
        report = {'gcs_path': 'gs://bucket/report.pdf'}
        insights = {
            'summary': 'Test summary',
            'treatment_effect': 0.05,
            'is_significant': True
        }
        
        # Run
        result = self.agent._distribute_to_cmo(report, insights)
        
        # Verify
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['recipient'], 'cmo@test.com')
        mock_smtp.return_value.__enter__.return_value.send_message.assert_called_once()
        
        # Cleanup
        if os.path.exists('tmp/test_report.pdf'):
            os.remove('tmp/test_report.pdf')

    @patch('src.agents.distributor_agent.requests.post')
    def test_distribute_to_marketing_ops(self, mock_post):
        # Setup mock
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        report = {'gcs_path': 'gs://bucket/report.pdf'}
        insights = {
            'incremental_lift_pct': 5.5,
            'is_significant': True,
            'confidence_level': 'High'
        }
        
        # Run
        result = self.agent._distribute_to_marketing_ops(report, insights)
        
        # Verify
        self.assertEqual(result['status'], 'success')
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], 'https://test-webhook')
        self.assertIn('5.50%', str(kwargs['json']))

    @patch('src.agents.distributor_agent.storage.Client')
    def test_distribute_to_data_team(self, mock_storage_client):
        # Setup mock
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_storage_client.return_value.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        
        all_reports = {
            'cmo': {'gcs_path': 'gs://bucket/cmo.pdf'},
            'data_team': {'gcs_path': 'gs://bucket/data.pdf'}
        }
        insights = {'key': 'value'}
        metadata = {'meta': 'data'}
        
        # Run
        result = self.agent._distribute_to_data_team(all_reports, insights, metadata)
        
        # Verify
        self.assertEqual(result['status'], 'success')
        self.assertTrue(result['path'].startswith('gs://test-bucket/analysis_runs/'))
        # Should upload insights, metadata, and copy 2 reports
        self.assertTrue(mock_blob.upload_from_string.called)
        self.assertTrue(mock_bucket.copy_blob.called)

if __name__ == '__main__':
    unittest.main()
