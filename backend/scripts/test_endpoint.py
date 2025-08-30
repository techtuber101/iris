#!/usr/bin/env python3
"""
Script to test the agent/start endpoint with authentication.
"""

import asyncio
import sys
import os
import requests
import json

def test_endpoint_with_auth():
    """Test the endpoint with a valid thread ID and authentication."""
    
    # Use an existing thread ID from the database
    thread_id = "0110b654-3a96-46ea-8b09-10861b936ab1"
    
    # Test without authentication (should return 401)
    print("Testing without authentication...")
    response = requests.post(
        f"http://localhost:8000/api/thread/{thread_id}/agent/start",
        headers={"Content-Type": "application/json"},
        json={
            "model_name": "gemini/gemini-2.5-pro",
            "enable_thinking": False,
            "reasoning_effort": "low",
            "stream": True,
            "enable_context_manager": False
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    print()
    
    # Test with invalid authentication (should return 401)
    print("Testing with invalid authentication...")
    response = requests.post(
        f"http://localhost:8000/api/thread/{thread_id}/agent/start",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer invalid_token"
        },
        json={
            "model_name": "gemini/gemini-2.5-pro",
            "enable_thinking": False,
            "reasoning_effort": "low",
            "stream": True,
            "enable_context_manager": False
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    print()
    
    # Test with non-existent thread ID (should return 404)
    print("Testing with non-existent thread ID...")
    fake_thread_id = "00000000-0000-0000-0000-000000000000"
    response = requests.post(
        f"http://localhost:8000/api/thread/{fake_thread_id}/agent/start",
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer invalid_token"
        },
        json={
            "model_name": "gemini/gemini-2.5-pro",
            "enable_thinking": False,
            "reasoning_effort": "low",
            "stream": True,
            "enable_context_manager": False
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    print()
    
    print("Test completed!")

if __name__ == "__main__":
    test_endpoint_with_auth()
