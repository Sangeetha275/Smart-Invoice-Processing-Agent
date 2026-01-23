import streamlit as st
import tempfile
import os
from DocumentExtractAgent.invoice_extraction_agent import process_invoice

st.set_page_config(page_title="AI Invoice Extractor", layout="centered")

st.title("🧾 AI Invoice Extractor")

uploaded_file = st.file_uploader(
    "Upload Invoice (PDF / Image / Text)",
    type=["pdf", "png", "jpg", "jpeg", "txt"]
)

if uploaded_file:
    # ✅ Preserve original file extension
    file_extension = os.path.splitext(uploaded_file.name)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        temp_path = tmp_file.name

    with st.spinner("Processing invoice..."):
        result = process_invoice(temp_path)

    st.subheader("📊 Extracted Invoice Data")
    st.json(result)

