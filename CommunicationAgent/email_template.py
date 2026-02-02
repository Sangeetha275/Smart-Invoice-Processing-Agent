def generate_email_subject(status, invoice_number):
    templates = {
        "APPROVED": f"Invoice Approved – {invoice_number}",
        "REJECTED": f"Invoice Rejected – {invoice_number}",
        "HOLD": f"Invoice On Hold – {invoice_number}"
    }
    return templates.get(status, f"Invoice Update – {invoice_number}")
 
 
def generate_email_body(vendor_name, invoice_number, invoice_date, status, reason=None):
 
    if status == "APPROVED":
        return f"""
Dear {vendor_name},
 
We are pleased to inform you that your invoice {invoice_number}
dated {invoice_date} has been approved.
 
Payment will be processed as per agreed terms.
 
Regards,
Accounts Payable Team
"""
 
    elif status == "REJECTED":
        return f"""
Dear {vendor_name},
 
Your invoice {invoice_number} dated {invoice_date} has been rejected.
 
Reason:
{reason}
 
Please correct and resubmit the invoice.
 
Regards,
Accounts Payable Team
"""
 
    elif status == "HOLD":
        return f"""
Dear {vendor_name},
 
Your invoice {invoice_number} dated {invoice_date}
is currently on hold.
 
Reason:
{reason}
 
Our team will review and update you shortly.
 
Regards,
Accounts Payable Team
"""
 