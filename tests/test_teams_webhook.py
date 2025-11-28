"""
Teams Webhook Test for Power Automate Workflows
This format works with "Post adaptive card in a chat or channel" workflows
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_workflow_format():
    """Send message in Power Automate workflow format"""
    
    webhook_url = os.environ.get('TEAMS_WEBHOOK_URL')
    
    if not webhook_url:
        print("❌ Error: TEAMS_WEBHOOK_URL not found in .env file")
        return False
    
    print(f"📍 Webhook URL: {webhook_url[:50]}...")
    
    # Power Automate expects this structure
    message = {
        "summary": "Incrementality Analysis Complete",  # Required by Power Automate
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": "📊 Incrementality Analysis Complete",
                            "weight": "Bolder",
                            "size": "Large",
                            "color": "Accent"
                        },
                        {
                            "type": "TextBlock",
                            "text": "Marketing Ops Report",
                            "spacing": "None",
                            "isSubtle": True
                        },
                        {
                            "type": "FactSet",
                            "facts": [
                                {
                                    "title": "Incremental Lift:",
                                    "value": "12.5%"
                                },
                                {
                                    "title": "Statistical Significance:",
                                    "value": "✅ Significant (p < 0.05)"
                                },
                                {
                                    "title": "Confidence Level:",
                                    "value": "95%"
                                }
                            ]
                        },
                        {
                            "type": "TextBlock",
                            "text": "This is a test of the Marketing Ops notification. Real reports will include actionable insights and recommendations.",
                            "wrap": True,
                            "spacing": "Medium"
                        }
                    ],
                    "actions": [
                        {
                            "type": "Action.OpenUrl",
                            "title": "View Full Report",
                            "url": "https://console.cloud.google.com/storage"
                        }
                    ]
                }
            }
        ]
    }
    
    try:
        print("📤 Sending adaptive card via Power Automate workflow...")
        response = requests.post(
            webhook_url,
            json=message,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📊 Response Body: {response.text}")
        
        if response.status_code in [200, 202]:
            print("\n✅ SUCCESS! Adaptive card sent to Teams.")
            print("👀 Check your Teams channel now - you should see a formatted card.")
            return True
        else:
            print(f"\n❌ Failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_simple_workflow_format():
    """Send the simplest possible adaptive card"""
    
    webhook_url = os.environ.get('TEAMS_WEBHOOK_URL')
    
    if not webhook_url:
        print("❌ Error: TEAMS_WEBHOOK_URL not found in .env file")
        return False
    
    # Minimal adaptive card
    message = {
        "summary": "Test Message",  # Required by Power Automate
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": "🧪 Test Message from GCP Reporting Orchestrator",
                            "weight": "Bolder",
                            "size": "Large"
                        },
                        {
                            "type": "TextBlock",
                            "text": "If you see this, your Power Automate workflow is working correctly!",
                            "wrap": True
                        }
                    ]
                }
            }
        ]
    }
    
    try:
        print("📤 Sending simple adaptive card...")
        response = requests.post(
            webhook_url,
            json=message,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code in [200, 202]:
            print("✅ SUCCESS! Check your Teams channel.")
            return True
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("TEAMS POWER AUTOMATE WORKFLOW TEST")
    print("="*60)
    
    # Test 1: Simple adaptive card
    print("\n[TEST 1] Sending simple adaptive card...")
    test1_result = test_simple_workflow_format()
    
    if test1_result:
        # Test 2: Full formatted card
        print("\n" + "="*60)
        print("[TEST 2] Sending full Marketing Ops format...")
        test_workflow_format()
    else:
        print("\n⚠️ Skipping Test 2 since Test 1 failed.")
        print("\nTroubleshooting:")
        print("1. Make sure you're using a Power Automate 'Post adaptive card' workflow")
        print("2. Verify the workflow is enabled in Teams")
        print("3. Check the workflow run history in Power Automate")
