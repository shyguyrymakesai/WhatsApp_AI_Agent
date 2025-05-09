# src/routers/lookup_cancel_router.py
from fastapi import APIRouter, Request
from src.handlers.booking_handler import cancel_booking, get_user_booking
from tools.whatsapp_snd_tool import SendWhatsappMsg

router = APIRouter()


@router.post("/incoming/lookup/cancel")
async def handle_cancel(request: Request):
    payload = await request.json()
    user_number = payload.get("number", "")
    if cancel_booking(user_number):
        msg = "✅ Your appointment has been canceled."
    else:
        msg = "⚠️ You don’t have any appointment to cancel."
    SendWhatsappMsg.invoke({"number": user_number, "message": msg})
    return {"status": "canceled"}


@router.post("/incoming/lookup/lookup")
async def handle_lookup(request: Request):
    payload = await request.json()
    user_number = payload.get("number", "")
    slot = get_user_booking(user_number)
    if slot:
        msg = f"📅 You are booked for {slot}!"
    else:
        msg = "😔 I couldn’t find an active booking for you."
    SendWhatsappMsg.invoke({"number": user_number, "message": msg})
    return {"status": "looked_up"}
