# src/receiver.py
"""
WhatsApp FastAPI webhook with intent routing, booking,
natural-language slots, reminders, and LLM fallback
"""
import os
import re
import socket
import sys
from fastapi import FastAPI, Request
import uvicorn

# allow imports from project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.handlers.intent_classifier import classify_intent, Intent
from src.handlers.booking_handler import (
    initialize_bookings_file,
    load_bookings,
    save_all_bookings,
    is_waiting_for_booking,
    set_waiting_for_booking,
    get_booking_options,
    get_user_booking,
    cancel_booking,
    save_individual_booking,
    slot_taken,
)
from src.handlers.day_detector import detect_day_request
from tools.whatsapp_snd_tool import SendWhatsappMsg
from src.agent.agent import Agent
from reminder_scheduler import start_scheduler
from tools.booking_tool import BookingTool
from utils.slot_parser import parse_slot

app = FastAPI()

# start the 60s reminder scheduler
start_scheduler(app)
# ensure bookings file exists
initialize_bookings_file()


@app.get("/ping")
async def ping():
    return {"status": "ok"}


@app.post("/incoming")
async def incoming(request: Request):
    payload = await request.json()
    user_number = payload.get("number", "")
    user_message = payload.get("message", "").strip()
    bookings = load_bookings()

    # 1️⃣ Awaiting email flow
    if bookings.get(user_number, {}).get("awaiting_email"):
        text = user_message.lower()
        if "skip" in text:
            bookings[user_number]["awaiting_email"] = False
            save_all_bookings(bookings)
            SendWhatsappMsg.invoke(
                {
                    "number": user_number,
                    "message": "👍 No problem – WhatsApp reminders only.",
                }
            )
            return {"status": "email skipped"}
        if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", user_message):
            bookings[user_number]["email"] = user_message
            bookings[user_number]["awaiting_email"] = False
            save_all_bookings(bookings)
            SendWhatsappMsg.invoke(
                {
                    "number": user_number,
                    "message": "✅ Great! I’ll email reminders too.",
                }
            )
            return {"status": "email saved"}
        SendWhatsappMsg.invoke(
            {
                "number": user_number,
                "message": "⚠️ That doesn’t look like an email. Send a valid address or say 'skip'.",
            }
        )
        return {"status": "awaiting valid email"}

    # classify intent and slot
    intent = classify_intent(user_message)
    natural = parse_slot(user_message)
    digit_sel = bool(re.fullmatch(r"[1-5]", user_message))

    # 2️⃣ Reschedule
    if intent is Intent.RESCHEDULE_APPT:
        current = get_user_booking(user_number)
        if current:
            cancel_booking(user_number)
            SendWhatsappMsg.invoke(
                {
                    "number": user_number,
                    "message": f"🔄 Your previous appointment at {current} has been canceled. Let's pick a new time!",
                }
            )
            intent = Intent.BOOK_APPT
        else:
            SendWhatsappMsg.invoke(
                {
                    "number": user_number,
                    "message": "😔 I don’t see an appointment to reschedule.",
                }
            )
            return {"status": "no booking to reschedule"}

    # 3️⃣ Clear stale waiting flag
    if is_waiting_for_booking(user_number, bookings) and not (
        natural or digit_sel or intent in {Intent.CHECK_DAY, Intent.BOOK_APPT}
    ):
        set_waiting_for_booking(user_number, bookings, False)
        save_all_bookings(bookings)

    # 4️⃣ Cancel appointment
    if intent is Intent.CANCEL_APPT:
        ok = cancel_booking(user_number)
        msg = (
            "✅ Your appointment has been canceled."
            if ok
            else "⚠️ You don’t have any appointment to cancel."
        )
        SendWhatsappMsg.invoke({"number": user_number, "message": msg})
        return {"status": "cancel"}

    # 5️⃣ Lookup appointment
    if intent is Intent.LOOKUP_APPT:
        slot = get_user_booking(user_number)
        msg = (
            f"📅 You are booked for {slot}!"
            if slot
            else "😔 I couldn’t find an active booking for you."
        )
        SendWhatsappMsg.invoke({"number": user_number, "message": msg})
        return {"status": "lookup"}

    # 6️⃣ Natural-language booking
    if intent is Intent.BOOK_APPT and natural:
        if slot_taken(natural, bookings, exclude_user=user_number):
            SendWhatsappMsg.invoke(
                {
                    "number": user_number,
                    "message": "⚠️ Sorry, that time was just booked. Please choose another slot.",
                }
            )
            return {"status": "slot collision"}
        save_individual_booking(user_number, natural)
        set_waiting_for_booking(user_number, bookings, False)
        save_all_bookings(bookings)
        SendWhatsappMsg.invoke(
            {
                "number": user_number,
                "message": f"✅ You're booked for {natural}! We'll remind you 24 h before.",
            }
        )
        # prompt email
        b = load_bookings()
        if not b[user_number].get("email"):
            b[user_number]["awaiting_email"] = True
            save_all_bookings(b)
            SendWhatsappMsg.invoke(
                {
                    "number": user_number,
                    "message": "📧 Got an email address? Reply or say 'skip'.",
                }
            )
            return {"status": "ask email"}
        return {"status": "booked natural"}

    # 7️⃣ Mid-booking override
    if is_waiting_for_booking(user_number, bookings) and natural:
        if slot_taken(natural, bookings, exclude_user=user_number):
            SendWhatsappMsg.invoke(
                {
                    "number": user_number,
                    "message": "⚠️ Sorry, that time was just booked. Please choose another slot.",
                }
            )
            return {"status": "slot collision"}
        save_individual_booking(user_number, natural)
        set_waiting_for_booking(user_number, bookings, False)
        save_all_bookings(bookings)
        SendWhatsappMsg.invoke(
            {
                "number": user_number,
                "message": f"✅ You're booked for {natural}! We'll remind you 24 h before.",
            }
        )
        b = load_bookings()
        if not b[user_number].get("email"):
            b[user_number]["awaiting_email"] = True
            save_all_bookings(b)
            SendWhatsappMsg.invoke(
                {
                    "number": user_number,
                    "message": "📧 Got an email address? Reply or say 'skip'.",
                }
            )
            return {"status": "ask email"}
        return {"status": "confirmed"}

    # 8️⃣ BookingTool fallback
    if intent is Intent.BOOK_APPT:
        result = BookingTool.run({"number": user_number, "user_message": user_message})
        if result.startswith("booked::"):
            slot = result.split("::", 1)[1]
            SendWhatsappMsg.invoke(
                {
                    "number": user_number,
                    "message": f"✅ You're booked for {slot}! We'll remind you 24 h before.",
                }
            )
            return {"status": "booked"}
        if result == "slot_taken":
            SendWhatsappMsg.invoke(
                {
                    "number": user_number,
                    "message": "⚠️ Sorry, that time was just booked. Please choose another slot.",
                }
            )
            return {"status": "slot collision"}

    # 9️⃣ Show menu
    if intent in {Intent.BOOK_APPT, Intent.CHECK_DAY}:
        day = detect_day_request(user_message) if intent is Intent.CHECK_DAY else None
        slots = get_booking_options(desired_day=day or "", raw=True)
        if not slots:
            SendWhatsappMsg.invoke(
                {"number": user_number, "message": "⚠️ No available slots right now."}
            )
            return {"status": "no slots"}
        top5 = slots[:5]
        set_waiting_for_booking(user_number, bookings, True)
        save_all_bookings(bookings)
        menu = "\n".join(f"{i+1}. {s}" for i, s in enumerate(top5))
        SendWhatsappMsg.invoke(
            {"number": user_number, "message": f"🔎 Available times:\n{menu}"}
        )
        return {"status": "menu shown"}

    # 🔟 LLM fallback with memory
    agent = Agent(user_id=user_number)
    tool, args = agent.think_llm(user_message)
    args.setdefault("number", user_number)
    args.setdefault("user_number", user_number)
    response = agent.act(tool, args, user_message)
    return {"status": "agent", "tool": tool, "args": args, "response": response}


def find_open_port(start: int = 8001) -> int:
    """Find an available port to avoid collisions."""
    for port in range(start, start + 20):
        with socket.socket() as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No available port found")


if __name__ == "__main__":
    port = find_open_port()
    with open("fastapi_port.txt", "w") as f:
        f.write(str(port))
    print(f"🚀 FastAPI server starting on port {port}")
    uvicorn.run("src.receiver:app", host="0.0.0.0", port=port, reload=True)
