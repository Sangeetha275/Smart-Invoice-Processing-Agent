def verify_gst_number(gst_number: str) -> dict:
    """
    MOCK GST API
    Used for demo / development to avoid rate limits & 403 errors
    """
    return {
        "mock": True,
        "result": {
            "source_output": {
                "gstin": gst_number
            }
        }
    }
