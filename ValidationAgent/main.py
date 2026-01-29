import json
from validation_agent import validate_invoice_from_json


if __name__ == "__main__":

    # -------------------- LOAD INVOICE JSON --------------------
    with open("input.json", "r") as f:
        invoice_data = json.load(f)

    # -------------------- VALIDATE INVOICE --------------------
    result = validate_invoice_from_json(invoice_data)

    # -------------------- PRINT JSON OUTPUT --------------------
    print("\nGST VALIDATION RESULT (JSON)\n")
    print(json.dumps(result, indent=4))

    # -------------------- SAVE OUTPUT TO JSON FILE --------------------
    with open("gst_validation_output.json", "w") as f:
        json.dump(result, f, indent=4)

    print("\n✅ Validation result saved to gst_validation_output.json\n")


