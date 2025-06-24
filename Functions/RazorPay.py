import os
import razorpay
import time

# 🔐 Razorpay credentials
RAZORPAY_KEY = os.getenv('RAZORPAY_KEY')
RAZORPAY_SECRET = os.getenv('RAZORPAY_SECRET')

if not RAZORPAY_KEY or not RAZORPAY_SECRET:
    raise ValueError("Razorpay credentials are missing. Set RAZORPAY_KEY and RAZORPAY_SECRET.")

# Initialize Razorpay client (ensure these are set properly in your app)
razorpay_client = razorpay.Client(auth=("RAZORPAY_KEY_ID", "RAZORPAY_SECRET"))

def check_payment_status(order_id: str, timeout_minutes: int = 20, poll_interval: int = 5) -> dict:
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

                if status == 'captured':
                    return {
                        "success": True,
                        "status": "paid",
                        "message": "Payment successful.",
                        "payment_id": payment_id,
                        "order_id": order_id
                    }

                elif status == 'failed':
                    return {
                        "success": True,
                        "status": "failed",
                        "message": "Payment failed.",
                        "payment_id": payment_id,
                        "order_id": order_id
                    }

            time.sleep(poll_interval)
            waited += poll_interval

        # If we reach here, it means no final status was found
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

