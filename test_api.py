#!/usr/bin/env python3
"""
Simple API testing script for ZipClip Backend
Tests health, processing, and status endpoints
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("\n=== Testing Health Endpoint ===")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_process_from_url():
    """Test processing from URL"""
    print("\n=== Testing Process Endpoint (URL) ===")
    try:
        payload = {
            "video_url": "https://youtu.be/dKMueTMW1Nw",
            "mode": "continuous",
            "add_subtitles": True,
            "target_duration": 120
        }
        response = requests.post(
            f"{BASE_URL}/api/process",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        return data.get("job_id") if response.status_code == 202 else None
    except Exception as e:
        print(f"Error: {e}")
        return None

def test_status(job_id):
    """Test status endpoint"""
    print(f"\n=== Testing Status Endpoint (Job: {job_id}) ===")
    try:
        response = requests.get(f"{BASE_URL}/api/status/{job_id}")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_list_jobs():
    """Test list jobs endpoint"""
    print("\n=== Testing List Jobs Endpoint ===")
    try:
        response = requests.get(f"{BASE_URL}/api/jobs")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print("ZipClip Backend API Tester")
    print(f"Base URL: {BASE_URL}")
    
    # Test 1: Health
    health_ok = test_health()
    if not health_ok:
        print("\n❌ Health check failed! Is the server running?")
        print(f"   Start the API with: bash run_api.sh")
        return
    
    print("\n✅ API is running!")
    
    # Test 2: List jobs
    test_list_jobs()
    
    # Test 3: Submit a job
    job_id = test_process_from_url()
    
    if job_id:
        print(f"\n✅ Job submitted successfully! ID: {job_id}")
        
        # Test 4: Check status
        time.sleep(2)  # Wait a bit before checking
        test_status(job_id)
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main()
