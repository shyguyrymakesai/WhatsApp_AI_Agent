# whatsapp_rcv_tool.py

from langchain_core.tools import tool


def receive_whatsapp_message(payload: dict) -> dict:
    """
    Receives incoming WhatsApp message payload.

    Args:
        payload (dict): Should include 'message' (text) and 'number' (sender's phone).

    Returns:
        dict: A structured object with user message and user phone number.
    """
    try:
        user_message = payload.get("message", "")
        user_number = payload.get("number", "")

        if not user_message or not user_number:
            raise ValueError("Payload missing required fields.")

        return {"user_message": user_message, "user_number": user_number}

    except Exception as e:
        return {"error": f"Failed to process incoming WhatsApp payload: {e}"}
