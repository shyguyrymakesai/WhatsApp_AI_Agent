from langchain.tools import StructuredTool
import requests
from pydantic import BaseModel



class WhatsAppInput(BaseModel):
    number: str
    message: str

def snd_msg_whatsapp(number :str, message : str) -> str:
    url = 'http://localhost:3000/send'
    payload = {
        'number': number,  # e.g., '15551234567'
        'message': message
    }
    
    print(f"🛠️ Inside snd_msg_whatsapp with payload: {payload}")  

    try:
        res = requests.post(url, json=payload)
        res.raise_for_status()
        print("✅ WhatsApp message sent.")
    except Exception as e:
        print("❌ Failed to send WhatsApp message:", e)

SendWhatsappMsg = StructuredTool.from_function(
    name = "SendWhatsappMsg",
    func = snd_msg_whatsapp,
    args_schema = WhatsAppInput, 
    description = "Use this to send a WhatsApp message to the user. Input should be the user's phone number and a message. The input will be passed to you in the following format: [number: 15555555, msg: example txt]"
)