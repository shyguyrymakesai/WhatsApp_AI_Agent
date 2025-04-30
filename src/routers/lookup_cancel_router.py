# src/routers/lookup_cancel_router.py
from fastapi import Request
from tools.whatsapp_snd_tool import SendWhatsappMsg
from handlers.booking_handler import cancel_booking, get_user_booking


async def handle_cancel(body: dict) -> dict:
    user = body["user_number"]
    if cancel_booking(user):
        txt = "✅ Your appointment has been canceled."
    else:
        txt = "⚠️ You don’t have any appointment to cancel."
    SendWhatsappMsg.invoke({"number": user, "message": txt})
    return {"status": "canceled"}


async def handle_lookup(body: dict) -> dict:
    user = body["user_number"]
    slot = get_user_booking(user)
    if slot:
        txt = f"📅 You are booked for {slot}!"
    else:
        txt = "😔 I couldn’t find an active booking for you."
    SendWhatsappMsg.invoke({"number": user, "message": txt})
    return {"status": "lookup"}
