import streamlit as st
import tempfile
import os
import json

from DocumentExtractAgent.invoice_extraction_agent import process_invoice
from DuplicateDetectionAgent.duplicate_detection_agent import DuplicateDetectionAgent

st.set_page_config(page_title="AI Invoice Processor", layout="centered")
st.title("🧾 AI Invoice Processor")

uploaded_file = st.file_uploader(
    "Upload Invoice (PDF / Image / Text)",
    type=["pdf", "png", "jpg", "jpeg", "txt"]
)

if uploaded_file:
    # -------------------- SAVE FILE --------------------
    file_extension = os.path.splitext(uploaded_file.name)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        temp_path = tmp_file.name

    # -------------------- DOCUMENT EXTRACTION --------------------
    with st.spinner("Extracting invoice data..."):
        result = process_invoice(temp_path)

    # Parse JSON safely
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except Exception:
            st.error("❌ Failed to parse extracted invoice data")
            st.stop()

    st.subheader("📄 Extracted Invoice Data")

    # -------------------- VENDOR EMAIL (MANDATORY) --------------------
    if not result.get("vendor_email"):
        st.warning("⚠️ Vendor email not found in invoice")

        manual_email = st.text_input(
            "Enter Vendor Email (required)",
            placeholder="vendor@example.com"
        )

        if not manual_email:
            st.info("Please enter vendor email to continue")
            st.stop()

        result["vendor_email"] = manual_email

    st.json(result)

    # -------------------- DUPLICATE DETECTION --------------------
    st.subheader("🔍 Duplicate Check")

    duplicate_agent = DuplicateDetectionAgent()

    duplicate_result = duplicate_agent.check_duplicate({
        "invoice_number": result.get("invoice_number"),
        "vendor_name": result.get("vendor_name"),
        "invoice_date": result.get("invoice_date"),
        "total_amount": result.get("total_amount")
    })

    # -------------------- DUPLICATE RESULT UI --------------------
    if duplicate_result["is_duplicate"]:
        st.error(
            f"🚨 DUPLICATE INVOICE ({duplicate_result['duplicate_type']})"
        )
        st.write(duplicate_result["message"])
        st.write(f"Confidence: {duplicate_result['confidence']:.2f}")

        st.info("⛔ Invoice processing stopped. Finance review required.")
        st.stop()

    else:
        st.success("✅ No duplicate found. Invoice can proceed.")
        st.write(f"Confidence: {duplicate_result['confidence']:.2f}")
