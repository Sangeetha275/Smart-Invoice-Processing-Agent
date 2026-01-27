import json
from validation_agent import validate_invoice_from_json


if __name__ == "__main__":

    # -------------------- LOAD INVOICE JSON --------------------
    with open("input.json", "r") as f:
        invoice_data = json.load(f)

    # -------------------- VALIDATE INVOICE --------------------
    result = validate_invoice_from_json(invoice_data)

    # -------------------- PRINT RESULT --------------------
    print("\nGST VALIDATION RESULT\n")
    for k, v in result.items():
        print(f"{k}: {v}")
