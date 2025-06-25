import os
import razorpay
import time
import requests
from requests.auth import HTTPBasicAuth

# 🔐 Razorpay credentials
RAZORPAY_KEY = os.getenv('RAZORPAY_KEY')
RAZORPAY_SECRET = os.getenv('RAZORPAY_SECRET')

if not RAZORPAY_KEY or not RAZORPAY_SECRET:
    raise ValueError("Razorpay credentials are missing. Set RAZORPAY_KEY and RAZORPAY_SECRET.")

# Initialize Razorpay client (ensure these are set properly in your app)
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY, RAZORPAY_SECRET))

# Function to get Razorpay balance
def get_razorpay_balance():
    url = "https://api.razorpay.com/v1/balance"

    response = requests.get(url, auth=HTTPBasicAuth(RAZORPAY_KEY, RAZORPAY_SECRET))

    if response.status_code == 200:
        data = response.json()
        balance_paise = data['balance']
        currency = data['currency']
        return data
    else:
        print("Failed to fetch balance:", response.status_code, response.text)
        return None

# Function to check payment status for a given order ID
def check_payment_status(order_id: str, timeout_minutes: int = 20, poll_interval: int = 5) -> dict:
    import time

    max_wait_seconds = timeout_minutes * 60
    waited = 0

    try:
        while waited < max_wait_seconds:
            try:
                payments = razorpay_client.order.payments(order_id)
            except Exception as fetch_err:
                return {
                    "success": False,
                    "status": "error",
                    "message": f"Error fetching payment details: {str(fetch_err)}",
                    "payment_id": None,
                    "order_id": order_id
                }

            for payment in payments.get('items', []):
                status = payment.get('status')
                payment_id = payment.get('id')
                method = payment.get('method')

                # Raw values in paise
                amount_paise = payment.get("amount", 0) or 0
                fee_paise = payment.get("fee", 0) or 0
                tax_paise = payment.get("tax", 0) or 0

                # Convert to INR
                amount_inr = round(amount_paise / 100, 2)
                fee_inr = round(fee_paise / 100, 2)
                tax_inr = round(tax_paise / 100, 2)

                # Method-specific fields
                method_details = {
                    "method": method,
                    "email": payment.get("email"),
                    "contact": payment.get("contact"),
                    "amount": amount_inr,
                    "razorpay_fee": fee_inr,
                    "gst": tax_inr,
                    "total_fee": fee_inr,  # Razorpay fee includes GST
                    "status": status
                }

                # Extract payment method specific data
                if method == "upi":
                    method_details["vpa"] = payment.get("vpa")
                    method_details["upi_transaction_id"] = payment.get("acquirer_data", {}).get("upi_transaction_id")

                elif method == "card":
                    method_details["card_id"] = payment.get("card_id")
                    card = payment.get("card", {})
                    method_details["card_details"] = {
                        "last4": card.get("last4"),
                        "network": card.get("network"),
                        "type": card.get("type"),
                        "issuer": card.get("issuer"),
                        "international": card.get("international"),
                    }

                elif method == "netbanking":
                    method_details["bank"] = payment.get("bank")

                elif method == "wallet":
                    method_details["wallet"] = payment.get("wallet")

                elif method == "emi":
                    method_details["emi_plan"] = payment.get("emi_plan")
                    method_details["emi_duration"] = payment.get("emi_duration")

                elif method == "bank_transfer":
                    method_details["bank_reference"] = payment.get("acquirer_data", {}).get("bank_transaction_id")

                elif method == "paylater":
                    method_details["provider"] = payment.get("provider")

                elif method == "cardless_emi":
                    method_details["provider"] = payment.get("provider")

                elif method == "cod":
                    method_details["description"] = "Cash on Delivery – manually collected"

                # Final status responses
                if status == 'captured':
                    return {
                        "success": True,
                        "status": "paid",
                        "message": "Payment successful.",
                        "payment_id": payment_id,
                        "order_id": order_id,
                        "payment_details": method_details
                    }

                elif status == 'failed':
                    return {
                        "success": True,
                        "status": "failed",
                        "message": "Payment failed.",
                        "payment_id": payment_id,
                        "order_id": order_id,
                        "payment_details": method_details
                    }

            # Sleep before polling again
            time.sleep(poll_interval)
            waited += poll_interval

        return {
            "success": True,
            "status": "timeout",
            "message": "No payment activity within the timeout window.",
            "payment_id": None,
            "order_id": order_id
        }

    except Exception as e:
        return {
            "success": False,
            "status": "error",
            "message": f"Internal error: {str(e)}",
            "payment_id": None,
            "order_id": order_id
        }

