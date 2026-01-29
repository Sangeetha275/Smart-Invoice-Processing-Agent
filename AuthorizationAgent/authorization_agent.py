import smtplib
import imaplib
import email
import time
import uuid
import snowflake.connector
from datetime import datetime
from email.message import EmailMessage
from email.utils import parseaddr
from bs4 import BeautifulSoup

# ================= CONFIG =================

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
IMAP_SERVER = "imap.gmail.com"

SENDER_EMAIL = "oli516537@gmail.com"
SENDER_PASSWORD = "jods woju uvrr mwkb"
MANAGER_EMAIL = "sudaroli224@gmail.com"

THRESHOLD = 50000

# ================= SNOWFLAKE CONFIG =================

SNOWFLAKE_CONFIG = {
    "user": "SUDAROLIGOPAL",
    "password": "SudaroliNageswari@2004",
    "account": "kvuunyb-hp15737",
    "warehouse": "COMPUTE_WH",
    "database": "SMART_INVOICE_DB",
    "schema": "AP_INVOICES",
    "role": "ACCOUNTADMIN"
}

SNOWFLAKE_TABLE = "SMART_INVOICE_DB.AP_INVOICES.INVOICES"

# ================= UTILS =================

def parse_amount(value):
    cleaned = str(value).replace(",", "").replace("₹", "").strip()
    amount = float(cleaned)
    if amount < 0:
        raise ValueError("Invalid invoice amount")
    return amount


def clean_email_body(raw_body: str) -> str:
    soup = BeautifulSoup(raw_body, "html.parser")
    return soup.get_text("\n").upper().strip()

# ================= SNOWFLAKE UPSERT =================

def upsert_invoice_snowflake(invoice, status):
    conn = snowflake.connector.connect(**SNOWFLAKE_CONFIG)
    cur = conn.cursor()

    cur.execute(f"""
        MERGE INTO {SNOWFLAKE_TABLE} t
        USING (
            SELECT
                %(invoice_number)s AS INVOICE_NUMBER,
                %(vendor_name)s AS VENDOR_NAME,
                %(invoice_date)s AS INVOICE_DATE,
                %(total_amount)s AS TOTAL_AMOUNT,
                %(gst_number)s AS GST_NUMBER,
                %(pan_number)s AS PAN_NUMBER,
                %(vendor_address)s AS VENDOR_ADDRESS,
                %(vendor_email)s AS VENDOR_EMAIL,
                %(product_name)s AS PRODUCT_NAME,
                %(status)s AS STATUS
        ) s
        ON t.INVOICE_NUMBER = s.INVOICE_NUMBER
           AND t.VENDOR_NAME = s.VENDOR_NAME
        WHEN MATCHED THEN UPDATE SET
            STATUS = s.STATUS
        WHEN NOT MATCHED THEN INSERT (
            INVOICE_NUMBER,
            VENDOR_NAME,
            INVOICE_DATE,
            TOTAL_AMOUNT,
            GST_NUMBER,
            PAN_NUMBER,
            VENDOR_ADDRESS,
            VENDOR_EMAIL,
            PRODUCT_NAME,
            STATUS
        ) VALUES (
            s.INVOICE_NUMBER,
            s.VENDOR_NAME,
            s.INVOICE_DATE,
            s.TOTAL_AMOUNT,
            s.GST_NUMBER,
            s.PAN_NUMBER,
            s.VENDOR_ADDRESS,
            s.VENDOR_EMAIL,
            s.PRODUCT_NAME,
            s.STATUS
        )
    """, {
        "invoice_number": invoice["invoice_number"],
        "vendor_name": invoice["vendor_name"],
        "invoice_date": invoice["invoice_date"],
        "total_amount": parse_amount(invoice["total_amount"]),
        "gst_number": invoice["gst_number"],
        "pan_number": invoice["pan_number"],
        "vendor_address": invoice["vendor_address"],
        "vendor_email": invoice["vendor_email"],
        "product_name": invoice["product_name"],
        "status": status
    })

    conn.commit()
    cur.close()
    conn.close()

    print("📊 Snowflake upsert successful")

# ================= EMAIL TO MANAGER =================

def send_manager_email(invoice, token):
    msg = EmailMessage()
    msg["From"] = SENDER_EMAIL
    msg["To"] = MANAGER_EMAIL
    msg["Subject"] = f"Approval Required: Invoice {invoice['invoice_number']}"

    msg.set_content(f"""
APPROVAL REQUEST

Invoice Number : {invoice['invoice_number']}
Vendor         : {invoice['vendor_name']}
Amount         : {invoice['total_amount']}

Reply with ONLY ONE WORD in the FIRST LINE:
APPROVED or REJECTED

Approval Token: {token}
""")

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)

    print("📧 Manager approval email sent")

# ================= READ MANAGER REPLY =================

def check_manager_reply(token, invoice_number, wait_seconds=300):
    print("🔍 Waiting for manager reply...")
    end_time = time.time() + wait_seconds

    while time.time() < end_time:
        try:
            mail = imaplib.IMAP4_SSL(IMAP_SERVER)
            mail.login(SENDER_EMAIL, SENDER_PASSWORD)
            mail.select("INBOX")

            _, data = mail.search(None, "ALL")
            for mail_id in reversed(data[0].split()[-20:]):
                _, msg_data = mail.fetch(mail_id, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])

                if parseaddr(msg.get("From"))[1].lower() != MANAGER_EMAIL.lower():
                    continue
                if invoice_number not in msg.get("Subject", ""):
                    continue

                raw_body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() in ["text/plain", "text/html"]:
                            raw_body += part.get_payload(decode=True).decode(errors="ignore")
                else:
                    raw_body = msg.get_payload(decode=True).decode(errors="ignore")

                body = clean_email_body(raw_body)
                if token not in body:
                    continue

                mail.logout()
                if body.startswith("APPROVED"):
                    return "APPROVED"
                if body.startswith("REJECTED"):
                    return "REJECTED"

            mail.logout()
        except Exception as e:
            print("⚠️ IMAP retry:", e)

        time.sleep(5)

    return None

# ================= COMMUNICATION AGENT =================

def communication_agent(vendor_name, vendor_email, invoice_number, status):
    payload = {
        "vendor_name": vendor_name,
        "vendor_email": vendor_email,
        "invoice_number": invoice_number,
        "status": status,
        "timestamp": datetime.utcnow().isoformat()
    }

    print("📣 Communication Agent called with payload:")
    print(payload)

# ================= AUTHORIZATION AGENT =================

def authorize_invoice(invoice):
    amount = parse_amount(invoice["total_amount"])

    # ---------- AUTO APPROVAL ----------
    if amount < THRESHOLD:
        status = "APPROVED"
        upsert_invoice_snowflake(invoice, status)
        communication_agent(
            invoice["vendor_name"],
            invoice["vendor_email"],
            invoice["invoice_number"],
            status
        )
        print("✅ Auto-approved")
        return

    # ---------- MANAGER APPROVAL ----------
    status = "PENDING"
    token = uuid.uuid4().hex.upper()

    upsert_invoice_snowflake(invoice, status)
    send_manager_email(invoice, token)

    decision = check_manager_reply(token, invoice["invoice_number"])
    if decision:
        upsert_invoice_snowflake(invoice, decision)
        communication_agent(
            invoice["vendor_name"],
            invoice["vendor_email"],
            invoice["invoice_number"],
            decision
        )
        print(f"✅ Manager decision received: {decision}")
    else:
        print("⚠️ No manager response (still PENDING)")

# ================= TEST =================

if __name__ == "__main__":
    test_invoice = {
        "invoice_number": "AIN2526003610503",
        "vendor_name": "Google Cloud Platform",
        "invoice_date": "2026-01-27",
        "total_amount": "67890",
        "gst_number": "29AACCG0527D1Z0",
        "pan_number": "AAJCAACCG0527DA9880A",
        "vendor_address": "3, RMZ Infinity – Tower E, Old Madras Road, Sadanandanagar, Bennigana Halli, Bengaluru, Karnataka 560016, India.",
        "vendor_email": "googlecloudplatform@gmail.com",
        "product_name": "Google BigQuery"
    }

    authorize_invoice(test_invoice)