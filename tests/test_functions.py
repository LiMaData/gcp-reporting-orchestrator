import unittest
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from functions.analysis.main import analyze_data
from functions.load.main import load_results

class TestCloudFunctions(unittest.TestCase):

    def test_analyze_data(self):
        request = MagicMock()
        request.get_json.return_value = {}
        
        response, status, headers = analyze_data(request)
        self.assertEqual(status, 200)
        data = json.loads(response)
        self.assertEqual(data['status'], 'success')
        self.assertTrue(len(data['data']) > 0)

    @patch('functions.load.main.bigquery.Client')
    def test_load_results(self, mock_bq):
        request = MagicMock()
        request.get_json.return_value = {
            'data': [{"id": "1", "prediction": "Test", "confidence": 0.9}]
        }
        
        mock_client = MagicMock()
        mock_bq.return_value = mock_client
        mock_client.insert_rows_json.return_value = [] # Success
        
        response, status = load_results(request)
        self.assertEqual(status, 200)
        self.assertEqual(response, 'Success')

if __name__ == '__main__':
    unittest.main()
