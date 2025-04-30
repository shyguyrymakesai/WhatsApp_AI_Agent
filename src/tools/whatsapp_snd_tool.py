from langchain.tools import StructuredTool
import requests
from pydantic import BaseModel
from src.utils.whatsapp import send_whatsapp_message as real_send_whatsapp_message


class WhatsAppInput(BaseModel):
    number: str
    message: str


def send_whatsapp_message(number: str, message: str):
    print(
        "📤 Attempting to send WhatsApp message with payload:",
        {"number": number, "message": message},
    )

    try:
        response = requests.post(
            "http://localhost:3000/send", json={"number": number, "message": message}
        )
        response.raise_for_status()
        print("✅ Message sent successfully!")
    except requests.exceptions.RequestException as e:
        print("❌ Failed to send WhatsApp message:", e)
        if "response" in locals() and response is not None:
            print("❌ Full response from Node:", response.text)
        else:
            print("❌ No response received.")
        raise e


# ⭐ THIS IS WHAT YOU NEED ⭐
SendWhatsappMsg = StructuredTool.from_function(
    func=send_whatsapp_message,
    name="SendWhatsappMsg",
    args_schema=WhatsAppInput,
    description="Use this to send a WhatsApp message to the user. Input format: {number, message}.",
)
