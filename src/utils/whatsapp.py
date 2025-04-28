import requests


def send_whatsapp_message(number: str, message: str) -> str:
    """
    Send a WhatsApp message via local server (like WhatsApp Web API / Venom / WPPConnect).

    Args:
        number (str): The WhatsApp number (example: "16367343546@c.us")
        message (str): The message text to send

    Returns:
        str: Status message
    """
    url = "http://localhost:3000/send"
    payload = {"number": number, "message": message}

    print(f"🛠️ Inside send_whatsapp_message with payload: {payload}")

    try:
        res = requests.post(url, json=payload)
        res.raise_for_status()
        print("✅ WhatsApp message sent successfully.")
        return "✅ WhatsApp message sent successfully."
    except Exception as e:
        error_msg = f"❌ Failed to send WhatsApp message: {e}"
        print(error_msg)
        return error_msg
