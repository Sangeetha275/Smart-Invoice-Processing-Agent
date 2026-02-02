import os
import re
import pytesseract
import pdfplumber
from PIL import Image
from dotenv import load_dotenv
from langchain_groq import ChatGroq

# -------------------- ENV --------------------
load_dotenv()

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# -------------------- LLM --------------------
llm = ChatGroq(
    model="openai/gpt-oss-120b",
    groq_api_key=os.getenv("GROQ_API_KEY"),
    temperature=0
)

# -------------------- REGEX --------------------
GST_REGEX = r"\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b"
PAN_REGEX = r"\b[A-Z]{5}\d{4}[A-Z]\b"

# -------------------- OCR --------------------
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text.strip()


def extract_text_from_image(image_path):
    return pytesseract.image_to_string(Image.open(image_path)).strip()


import os

def extract_text_from_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return extract_text_from_pdf(file_path)

    elif ext in [".png", ".jpg", ".jpeg"]:
        return extract_text_from_image(file_path)

    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()

    else:
        raise ValueError(f"Unsupported file type: {ext}")


# -------------------- LLM FIELD EXTRACTION --------------------
def extract_field(text, field_name, labels):
    prompt = f"""
Extract ONLY the {field_name} from the invoice.

Rules:
- Use ONLY invoice text
- Do NOT infer or calculate
- If not found return ""
- Return ONLY the value

Common labels:
{labels}

Invoice text:
{text}
"""
    return llm.invoke(prompt).content.strip()

# -------------------- REGEX EXTRACTION --------------------
def extract_gst_number(text):
    match = re.search(GST_REGEX, text)
    return match.group() if match else ""


def extract_pan_number(text):
    match = re.search(PAN_REGEX, text)
    return match.group() if match else ""

# -------------------- ADDRESS EXTRACTION --------------------
def extract_vendor_address(text):
    prompt = f"""
Extract ONLY the seller/vendor address exactly as written.

Rules:
- Do NOT summarize
- Do NOT infer
- If not found return ""
- Return ONLY the address

Invoice text:
{text}
"""
    return llm.invoke(prompt).content.strip()

# -------------------- LINE ITEMS --------------------
def extract_line_items(text):
    items = []
    lines = text.split("\n")

    for line in lines:
        line = line.strip()
        match = re.search(r"(.+?)\s+(\d+)\s+(\d+\.\d{2})$", line)
        if match:
            items.append({
                "description": match.group(1).strip(),
                "quantity": int(match.group(2)),
                "price": float(match.group(3))
            })
    return items

def llm_result(file_path):
    CHECK=llm.invoke(f"{file_path} extract invoice details from such as invoice no,gst id,total amount , vendor name etc").content.strip()
    return CHECK
# -------------------- MAIN PIPELINE --------------------
def process_invoice(file_path):
    text = extract_text_from_file(file_path)

    result = {
        "invoice_number": extract_field(
            text, "Invoice Number", "Invoice No, Invoice Number, Inv No"
        ),
        "vendor_name": extract_field(
            text, "Vendor Name", "From, Seller, Vendor, Company Name"
        ),
        "invoice_date": extract_field(
            text, "Invoice Date", "Invoice Date, Date"
        ),
        "due_date": extract_field(
            text, "Due Date", "Due Date, Payment Due"
        ),
        "total_amount": extract_field(
            text, "Total Amount", "Total, Grand Total, Amount Payable"
        ),
        "gst_number": extract_gst_number(text),
        "pan_number": extract_pan_number(text),
        "vendor_address": extract_vendor_address(text),
        "line_items": extract_line_items(text),
        "llm_check": llm_result(text)
    }
    print(result)
    final = llm.invoke(
    f"""
Return ONLY a JSON object matching this schema:

{{
  "invoice_number": "",
  "vendor_name": "",
  "invoice_date": "",
  "total_amount": "",
  "gst_number": "",
  "pan_number": "",
  "vendor_address": "",
  "vendor_email": "",
  "product_name": ""
}}

Extract the key invoice details from the following text in JSON format: {text}, from the {result} extract mainly from the llm_check json key and check its gst number,pan,invoice no from the other keys whether the keys are correct and  fetch these details only invoice number, vendor name, invoice date,  total amount, GST number, PAN number, vendor address, vendor email,product name, vendor name fetch these details alone know and invoice date should be in this format '2026-01-02'
"""
).content.strip()
    
    return final
