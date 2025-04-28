from langchain.tools import StructuredTool
import requests
from pydantic import BaseModel
from utils.whatsapp import send_whatsapp_message


class WhatsAppInput(BaseModel):
    number: str
    message: str


SendWhatsappMsg = StructuredTool.from_function(
    name="SendWhatsappMsg",
    func=send_whatsapp_message,
    args_schema=WhatsAppInput,
    description="Use this to send a WhatsApp message to the user. Input should be the user's phone number and a message. The input will be passed to you in the following format: [number: 15555555, message: example text]",
)
