from langchain.tools import StructuredTool


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


# Export it as a StructuredTool (optional if you need it for LLM routing)
ReceiveWhatsappMsg = StructuredTool.from_function(
    func=receive_whatsapp_message,
    name="ReceiveWhatsappMsg",
    description="Parse incoming WhatsApp payload into clean {user_message, user_number} dict.",
)
