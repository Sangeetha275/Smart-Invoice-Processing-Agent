import requests
from config import RAPIDAPI_KEY, RAPIDAPI_HOST, GST_VERIFY_URL

def verify_gst_number(gst_number: str) -> dict:
    payload = {
        "task_id": "gst_validation_task",
        "group_id": "gst_validation",
        "data": {
            "gstin": gst_number
        }
    }

    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST,
        "Content-Type": "application/json"
    }

    response = requests.post(GST_VERIFY_URL, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()
