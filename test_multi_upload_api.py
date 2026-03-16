import requests
import os
import json

def test_multi_upload():
    url = "http://localhost:8000/api/process"
    
    # Create dummy files for testing
    with open("test_v1.mp4", "wb") as f:
        f.write(b"dummy video content 1")
    with open("test_v2.mp4", "wb") as f:
        f.write(b"dummy video content 2")
    with open("test_img.jpg", "wb") as f:
        f.write(b"dummy image content")
        
    try:
        files = [
            ('files', ('test_v1.mp4', open('test_v1.mp4', 'rb'), 'video/mp4')),
            ('files', ('test_v2.mp4', open('test_v2.mp4', 'rb'), 'video/mp4')),
            ('files', ('test_img.jpg', open('test_img.jpg', 'rb'), 'image/jpeg')),
        ]
        
        data = {
            'mode': 'continuous',
            'add_subtitles': 'true',
            'target_duration': '60'
        }
        
        print("Submitting multi-file job...")
        response = requests.post(url, files=files, data=data)
        
        if response.status_code == 200:
            job = response.json()
            print(f"Job created successfully! Job ID: {job['job_id']}")
            print(f"Status: {job['status']}")
        else:
            print(f"Failed to create job: {response.status_code}")
            print(response.text)
            
    finally:
        # Clean up dummy files
        for f in ["test_v1.mp4", "test_v2.mp4", "test_img.jpg"]:
            if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    test_multi_upload()
