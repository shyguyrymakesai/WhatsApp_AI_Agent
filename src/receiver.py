# src/receiver.py
import re
import os
import socket
import sys

from fastapi import FastAPI, Request
from handlers.intent_classifier import classify_intent, Intent
from handlers.booking_handler import (
    initialize_bookings_file,
    load_bookings,
    save_all_bookings,
    is_waiting_for_booking,
    set_waiting_for_booking,
    get_booking_options,
    get_user_booking,
    save_individual_booking,
    slot_taken,
)
from handlers.day_detector import detect_day_request
from handlers.slot_picker import pick_slot_from_reply

from routers.email_router import handle_email
from routers.lookup_cancel_router import handle_cancel, handle_lookup
from routers.booking_router import handle_booking
from routers.fallback_router import handle_fallback

from tools.whatsapp_rcv_tool import receive_whatsapp_message
from tools.whatsapp_snd_tool import SendWhatsappMsg
from tools.time_tool import GetTime
from reminder_scheduler import start_scheduler
from memory.memory_client import get_user_memory, save_user_memory

app = FastAPI()
start_scheduler(app)
initialize_bookings_file()


@app.post("/incoming")
async def orchestrate(request: Request):
    payload = await request.json()
    extracted = receive_whatsapp_message(payload)
    if "error" in extracted:
        return {"status": "error", "details": extracted["error"]}

    user = extracted["user_number"]
    msg = extracted["user_message"].strip()
    bookings = load_bookings()
    memory = get_user_memory(user)

    # 1) Email-collection flow has top priority
    if bookings.get(user, {}).get("awaiting_email"):
        return await handle_email({"user_number": user, "user_message": msg})

    # 2) Intent classification
    intent = classify_intent(msg)

    # 3) Cancel or Lookup
    if intent is Intent.CANCEL_APPT:
        return await handle_cancel({"user_number": user})
    if intent is Intent.LOOKUP_APPT:
        return await handle_lookup({"user_number": user})

    # 4) Reschedule => cancel + fallthrough to BOOK_APPT
    if intent is Intent.RESCHEDULE_APPT:
        if get_user_booking(user):
            await handle_cancel({"user_number": user})
            intent = Intent.BOOK_APPT
        else:
            SendWhatsappMsg.invoke(
                {
                    "number": user,
                    "message": "😔 I don’t see an existing appointment to reschedule.",
                }
            )
            return {"status": "no booking to reschedule"}

    # 5) Mid-booking flow: check for natural slot or delegate
    if is_waiting_for_booking(user, bookings):
        from tools.booking_tool import _parse_natural_slot

        natural = _parse_natural_slot(msg)
        if natural:
            if slot_taken(natural, exclude_user=user):
                SendWhatsappMsg.invoke(
                    {
                        "number": user,
                        "message": "⚠️ Sorry, that time was just booked. Please choose another slot.",
                    }
                )
                return {"status": "collision"}

            save_individual_booking(user, natural)
            SendWhatsappMsg.invoke(
                {
                    "number": user,
                    "message": f"✅ You're booked for {natural}! We'll remind you 24 h before.",
                }
            )
            set_waiting_for_booking(user, bookings, False)
            b = load_bookings()
            if not b[user].get("email"):
                SendWhatsappMsg.invoke(
                    {
                        "number": user,
                        "message": "📧 Got an email address? Just reply with it, or say 'skip'.",
                    }
                )
                b[user]["awaiting_email"] = True
                save_all_bookings(b)
                return {"status": "ask_email"}
            save_all_bookings(bookings)
            return {"status": "confirmed"}

        # No natural slot, delegate to booking router
        return await handle_booking({"user_number": user, "user_message": msg})

    # 6) First-touch BOOK_APPT
    if intent is Intent.BOOK_APPT:
        nat_try = await handle_booking({"user_number": user, "user_message": msg})
        if nat_try.get("status") in ("booked", "collision"):
            return nat_try
        # fall through to menu

    # 7) Show menu for BOOK_APPT or CHECK_DAY
    if intent in (Intent.BOOK_APPT, Intent.CHECK_DAY):
        day = detect_day_request(msg) if intent is Intent.CHECK_DAY else None
        slots = get_booking_options(desired_day=day, raw=True)[:5]
        if not slots:
            SendWhatsappMsg.invoke(
                {"number": user, "message": "⚠️ No available slots for that day."}
            )
            return {"status": "no slots"}

        from collections import defaultdict

        user_shown = defaultdict(list)
        user_shown[user] = slots
        set_waiting_for_booking(user, bookings, True)
        save_all_bookings(bookings)
        menu = "🔎 Available times:\n" + "\n".join(
            f"{i+1}. {s}" for i, s in enumerate(slots)
        )
        SendWhatsappMsg.invoke({"number": user, "message": menu})
        return {"status": "show_menu"}

    # 8) Fallback to LLM
    return await handle_fallback({"user_number": user, "user_message": msg})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.receiver:app", host="0.0.0.0", port=8001, reload=True)
