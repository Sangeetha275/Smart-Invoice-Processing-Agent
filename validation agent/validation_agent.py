from gst_api import verify_gst_number
from gst_calculations import calculate_gst_components


def validate_invoice_from_json(invoice: dict) -> dict:
    """
    Validates invoice GST details using:
    - Vendor GST vs Government API
    - Vendor GST vs Invoice GST
    - GST calculation vs actual total
    """

    # -------------------- EXTRACT FIELDS FROM JSON --------------------
    vendor_gst = invoice["gst_number"]                 # GST entered by vendor
    invoice_gst = invoice["gst_number"]                # GST extracted from invoice
    invoice_amount_without_gst = float(invoice["amount_without_gst"])
    gst_rate = float(invoice["gst_rate"])
    actual_grand_total = float(invoice["total_amount"])
    interstate = invoice.get("interstate", True)

    # -------------------- GST API VERIFICATION --------------------
    api_result = verify_gst_number(vendor_gst)
    api_gst = api_result["result"]["source_output"]["gstin"]

    # -------------------- GST MATCH CHECKS --------------------
    vendor_vs_api = vendor_gst == api_gst
    vendor_vs_invoice = vendor_gst == invoice_gst

    # -------------------- GST CALCULATION --------------------
    gst_calc = calculate_gst_components(
        invoice_amount_without_gst,
        gst_rate,
        interstate
    )

    expected_total = gst_calc["expected_grand_total"]
    difference = abs(expected_total - actual_grand_total)

    # -------------------- FINAL VALIDATION STATUS --------------------
    if not vendor_vs_api:
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

    if vendor_vs_api:
        confidence_score += 40
    if vendor_vs_invoice:
        confidence_score += 30
    if difference <= 1:
        confidence_score += 20
    if difference <= 0.1:
        confidence_score += 10

    # -------------------- FINAL OUTPUT --------------------
    return {
        "invoice_number": invoice["invoice_number"],
        "vendor_name": invoice["vendor_name"],
        "vendor_email": invoice["vendor_email"],
        "vendor_address": invoice["vendor_address"],
        "product_name": invoice["product_name"],

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
