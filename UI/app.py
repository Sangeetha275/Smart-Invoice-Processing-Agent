import streamlit as st
import tempfile
import os
from Orchestrator.invoice_workflow import invoice_workflow

st.set_page_config(page_title="AI Invoice Processor", layout="wide")
st.title("🧾 Smart Invoice Processing")

uploaded_file = st.file_uploader(
    "Upload Invoice",
    type=["pdf", "png", "jpg", "jpeg", "txt"]
)

if uploaded_file:
    ext = os.path.splitext(uploaded_file.name)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(uploaded_file.getbuffer())
        file_path = tmp.name

    with st.spinner("Processing invoice using AI agents..."):
        result = invoice_workflow.invoke({
            "file_path": file_path
        })

    # -------------------- MANDATORY VENDOR EMAIL --------------------
    extracted = result["extracted_invoice"]

    if not extracted.get("vendor_email"):
        st.warning("⚠️ Vendor email not found in invoice")

        vendor_email = st.text_input(
            "Enter Vendor Email (required to proceed)",
            placeholder="vendor@example.com"
        )

        if not vendor_email:
            st.info("Please provide vendor email to continue processing.")
            st.stop()

        # Inject email back into extracted invoice
        extracted["vendor_email"] = vendor_email

    # -------------------- TABS --------------------
    tab1, tab2, tab3 = st.tabs(
        ["📄 Extracted Invoice", "🔍 Duplicate Check", "✅ GST Validation"]
    )

    with tab1:
        st.json(extracted)

    with tab2:
        dup = result["duplicate_result"]
        if dup["is_duplicate"]:
            st.error(f"🚨 DUPLICATE ({dup['duplicate_type']})")
            st.write(dup["message"])
            st.write(f"Confidence: {dup['confidence']}")
        else:
            st.success("✅ No duplicate found")
            st.write(f"Confidence: {dup['confidence']}")

    with tab3:
        if result.get("validation_result"):
            st.json(result["validation_result"])
        else:
            st.info("Validation skipped due to duplicate invoice")
