from CommunicationAgent.email_template import (
    generate_email_subject,
    generate_email_body
)
 
def generate_email(vendor_name, invoice_number, invoice_date, status, reason=None):
 
    subject = generate_email_subject(status, invoice_number)
    body = generate_email_body(
        vendor_name,
        invoice_number,
        invoice_date,
        status,
        reason
    )
 
    return subject, body