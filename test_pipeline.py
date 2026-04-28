import os
import requests
import time

BASE_URL = "http://127.0.0.1:8080/api/v1"
FILE_PATH = r"c:\Users\swast\OneDrive\Desktop\Bro\FairAI\Model Training\fairlens_dataset_unstructured (1).csv"

def run():
    print("Init upload...")
    try:
        res = requests.post(f"{BASE_URL}/uploads/init", json={"filename": "fairlens_dataset_unstructured (1).csv"})
        res.raise_for_status()
    except Exception as e:
        print(f"Failed to connect or init upload: {e}")
        return

    data = res.json()
    upload_url = data["upload_url"]
    file_uri = data["file_uri"]
    
    print(f"Uploading to {upload_url}...")
    full_upload_url = upload_url if upload_url.startswith("http") else f"http://127.0.0.1:8080{upload_url}"
    
    with open(FILE_PATH, "rb") as f:
        files = {"file": ("fairlens_dataset_unstructured (1).csv", f, "text/csv")}
        up_res = requests.post(full_upload_url, files=files)
        up_res.raise_for_status()
        
    print("Submitting job...")
    job_req = {
        "file_uri": file_uri,
        "config": {
            "label_column": "shortlisted",
            "protected_attributes": ["gender", "college_tier", "region"]
        }
    }
    job_res = requests.post(f"{BASE_URL}/jobs/debias", json=job_req)
    job_res.raise_for_status()
    job_data = job_res.json()
    job_id = job_data["job_id"]
    
    print(f"Job {job_id} submitted. Polling status...")
    while True:
        status_res = requests.get(f"{BASE_URL}/jobs/{job_id}")
        status_res.raise_for_status()
        status_data = status_res.json()
        status = status_data["job"]["status"]
        print(f"Status: {status}")
        if status in ("completed", "failed"):
            print("Final state:", status_data["job"])
            break
        time.sleep(1)

if __name__ == "__main__":
    run()
