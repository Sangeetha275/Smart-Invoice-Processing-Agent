from ValidationAgent.gst_api import verify_gst_number
from ValidationAgent.gst_calculations import calculate_gst_components


def validate_invoice_from_json(invoice: dict) -> dict:
    """
    Safely validates invoice GST details.
    Handles GST API failures without crashing.
    """

    # -------------------- EXTRACT FIELDS --------------------
    vendor_gst = invoice.get("gst_number", "").strip()
    invoice_gst = invoice.get("gst_number", "").strip()
    invoice_amount_without_gst = float(invoice.get("amount_without_gst", 0))
    gst_rate = float(invoice.get("gst_rate", 18))
    actual_grand_total = float(invoice.get("total_amount", 0))
    interstate = invoice.get("interstate", True)

    # -------------------- GST API CALL --------------------
    api_gst = None
    api_error = None

    try:
        api_result = verify_gst_number(vendor_gst)

        # SAFE PARSING
        if (
            isinstance(api_result, dict)
            and "result" in api_result
            and "source_output" in api_result["result"]
        ):
            api_gst = api_result["result"]["source_output"].get("gstin")
        else:
            api_error = api_result.get("message", "GST verification failed")

    except Exception as e:
        api_error = str(e)

    # -------------------- MATCH CHECKS --------------------
    vendor_vs_api = api_gst is not None and vendor_gst == api_gst
    vendor_vs_invoice = vendor_gst == invoice_gst

    # -------------------- GST CALCULATION --------------------
    gst_calc = calculate_gst_components(
        invoice_amount_without_gst,
        gst_rate,
        interstate
    )

    expected_total = gst_calc["expected_grand_total"]
    difference = abs(expected_total - actual_grand_total)

    # -------------------- FINAL STATUS --------------------
    if api_error:
        status = "GST_API_ERROR"
        message = f"GST verification failed: {api_error}"

    elif not vendor_vs_api:
        status = "INVALID_VENDOR_GST"
        message = "Vendor GST is not valid as per government records"

    elif not vendor_vs_invoice:
        status = "GST_OWNER_MISMATCH"
        message = "Invoice GST does not belong to the vendor"

    elif difference > 1:
        status = "AMOUNT_MISMATCH"
        message = "GST calculation mismatch"

    else:
        status = "MATCHED"
        message = "Invoice and GST validation successful"

    # -------------------- CONFIDENCE SCORE --------------------
    confidence_score = 0

    if api_gst:
        confidence_score += 40
    if vendor_vs_invoice:
        confidence_score += 30
    if difference <= 1:
        confidence_score += 20
    if difference <= 0.1:
        confidence_score += 10

    # -------------------- FINAL OUTPUT --------------------
    return {
        "invoice_number": invoice.get("invoice_number"),
        "vendor_name": invoice.get("vendor_name"),
        "vendor_email": invoice.get("vendor_email"),
        "vendor_address": invoice.get("vendor_address"),
        "product_name": invoice.get("product_name"),

        "vendor_gst": vendor_gst,
        "invoice_gst": invoice_gst,
        "api_verified_gst": api_gst,

        "vendor_vs_api_match": vendor_vs_api,
        "vendor_vs_invoice_match": vendor_vs_invoice,

        **gst_calc,

        "actual_grand_total": round(actual_grand_total, 2),
        "difference": round(difference, 2),

        "validation_status": status,
        "message": message,
        "confidence_score": confidence_score
    }
