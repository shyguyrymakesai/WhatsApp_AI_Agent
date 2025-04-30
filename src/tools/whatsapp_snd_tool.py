# src/tools/whatsapp_snd_tool.py
from langchain.tools import StructuredTool
import requests
from pydantic import BaseModel
from src.utils.whatsapp import send_whatsapp_message as real_send_whatsapp_message


class WhatsAppInput(BaseModel):
    number: str
    message: str


def send_whatsapp_message(number: str, message: str):
    """
    Send a WhatsApp message via the local Node.js sender.
    On failure, log the error but do not raise, to keep the FastAPI server running.
    """
    payload = {"number": number, "message": message}
    print("📤 Attempting to send WhatsApp message with payload:", payload)

    try:
        response = requests.post("http://localhost:3000/send", json=payload, timeout=5)
        response.raise_for_status()
        print("✅ Message sent successfully!")
    except requests.exceptions.RequestException as e:
        print("❌ Failed to send WhatsApp message:", e)
        # swallow exception to avoid crashing the webhook
    # No exception is raised, tool returns None


SendWhatsappMsg = StructuredTool.from_function(
    func=send_whatsapp_message,
    name="SendWhatsappMsg",
    args_schema=WhatsAppInput,
    description="Use this to send a WhatsApp message to the user. Input format: {number, message}.",
)
