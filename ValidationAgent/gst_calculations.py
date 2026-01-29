def calculate_gst_components(
    amount_without_gst: float,
    gst_rate: float,
    interstate: bool
) -> dict:
    total_gst = amount_without_gst * (gst_rate / 100)

    if interstate:
        igst = total_gst
        cgst = 0
        sgst = 0
    else:
        igst = 0
        cgst = total_gst / 2
        sgst = total_gst / 2

    grand_total = amount_without_gst + total_gst

    return {
        "amount_without_gst": round(amount_without_gst, 2),
        "gst_rate_percentage": gst_rate,
        "total_gst": round(total_gst, 2),
        "igst": round(igst, 2),
        "cgst": round(cgst, 2),
        "sgst": round(sgst, 2),
        "expected_grand_total": round(grand_total, 2)
    }
