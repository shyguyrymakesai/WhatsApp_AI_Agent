# src/routers/booking_router.py
from fastapi import Request
from tools.booking_tool import BookingTool
from tools.whatsapp_snd_tool import SendWhatsappMsg


async def handle_booking(body: dict) -> dict:
    user = body["user_number"]
    msg = body["user_message"].strip()

    result = BookingTool.run({"number": user, "user_message": msg})

    if result.startswith("booked::"):
        slot = result.split("::", 1)[1]
        SendWhatsappMsg.invoke(
            {
                "number": user,
                "message": f"✅ You're booked for {slot}! We'll remind you 24 h before.",
            }
        )
        return {"status": "booked"}

    if result == "slot_taken":
        SendWhatsappMsg.invoke(
            {
                "number": user,
                "message": "⚠️ Sorry, that time was just booked. Please choose another slot.",
            }
        )
        return {"status": "collision"}

    if result == "ask_day":
        SendWhatsappMsg.invoke(
            {
                "number": user,
                "message": "📅 Sure! Which day would you like an appointment?",
            }
        )
        return {"status": "ask_day"}

    if result.startswith("offer::"):
        slots = result.split("::", 1)[1]
        SendWhatsappMsg.invoke(
            {"number": user, "message": f"🔎 Available times:\n{slots}"}
        )
        return {"status": "offer_slots"}

    return {"status": "unrecognized"}
