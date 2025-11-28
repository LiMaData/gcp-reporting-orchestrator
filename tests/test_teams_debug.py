"""
Teams Debug Script - Brute force format testing
Tries multiple formats to see what actually renders in the channel.
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

WEBHOOK_URL = os.environ.get('TEAMS_WEBHOOK_URL')

def send_payload(name, payload):
    print(f"\n--- Testing: {name} ---")
    try:
        response = requests.post(
            WEBHOOK_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        if response.status_code == 200:
            print("✅ API accepted it. Check Teams!")
        else:
            print("❌ API rejected it.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if not WEBHOOK_URL:
        print("❌ No TEAMS_WEBHOOK_URL found")
        exit(1)

    print(f"Targeting: {WEBHOOK_URL[:60]}...")

    # TEST 1: Pure Text (Workflow specific)
    # Some workflows just want a "text" field
    payload_1 = {
        "type": "message",
        "text": "Test 1: Simple text message payload"
    }
    send_payload("1. Simple Text Object", payload_1)

    # TEST 2: Adaptive Card v1.0 (Most compatible)
    # Using the 'attachments' structure which is standard for workflows
    payload_2 = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.0",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": "Test 2: Adaptive Card v1.0",
                            "size": "large"
                        }
                    ]
                }
            }
        ]
    }
    send_payload("2. Adaptive Card v1.0", payload_2)

    # TEST 3: Adaptive Card v1.2 (Standard)
    payload_3 = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.2",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": "Test 3: Adaptive Card v1.2",
                            "weight": "bolder"
                        }
                    ]
                }
            }
        ]
    }
    send_payload("3. Adaptive Card v1.2", payload_3)
    
    # TEST 4: The "Summary" field fix (What we just tried)
    payload_4 = {
        "summary": "Test 4 Summary",
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
                            "text": "Test 4: With Summary Field",
                            "weight": "bolder"
                        }
                    ]
                }
            }
        ]
    }
    send_payload("4. With Summary Field", payload_4)
