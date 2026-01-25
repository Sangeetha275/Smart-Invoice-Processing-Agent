import streamlit as st
import tempfile
import os
import json
from DocumentExtractAgent.invoice_extraction_agent import process_invoice

st.set_page_config(page_title="AI Invoice Extractor", layout="centered")

st.title("🧾 AI Invoice Extractor")

uploaded_file = st.file_uploader(
    "Upload Invoice (PDF / Image / Text)",
    type=["pdf", "png", "jpg", "jpeg", "txt"]
)

if uploaded_file:
    # Preserve original extension
    file_extension = os.path.splitext(uploaded_file.name)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        temp_path = tmp_file.name

    with st.spinner("Processing invoice..."):
        result = process_invoice(temp_path)

    # If result is string JSON, convert to dict safely
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except Exception:
            st.error("Failed to parse invoice output")
            st.stop()

    st.subheader("📊 Extracted Invoice Data")

    # ✅ If vendor_email missing → ask user
    if not result.get("vendor_email"):
        st.warning("Vendor email not found in invoice. Please enter manually.")

        manual_email = st.text_input(
            "Enter Vendor Email",
            placeholder="vendor@example.com"
        )

        if manual_email:
            result["vendor_email"] = manual_email

    st.json(result)
