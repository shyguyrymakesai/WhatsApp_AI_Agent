# src/receiver.py
# -----------------------------------------------------------
# WhatsApp FastAPI webhook with intent routing, booking,
# natural-language slots, reminders, and LLM fallback
# -----------------------------------------------------------
import os, re, socket, sys
from collections import defaultdict
from fastapi import FastAPI, Request
import uvicorn

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ── project imports ─────────────────────────────────────────
from tools.whatsapp_rcv_tool import receive_whatsapp_message
from tools.whatsapp_snd_tool import SendWhatsappMsg
from tools.booking_tool import BookingTool, _parse_natural_slot
from tools.time_tool import GetTime
from agent.agent import Agent

from handlers.booking_handler import (
    initialize_bookings_file,
    cancel_booking,
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
from handlers.intent_classifier import classify_intent, Intent
from handlers.slot_picker import pick_slot_from_reply
from memory.memory_client import save_user_memory, get_user_memory
from reminder_scheduler import start_scheduler

# ── FastAPI & globals ───────────────────────────────────────
app = FastAPI()
start_scheduler(app)  # <── runs reminders every 60 s

agent = Agent()
initialize_bookings_file()
user_shown_slots: defaultdict[str, list] = defaultdict(list)


# ── helpers ─────────────────────────────────────────────────
def fill_user_number(tool_args: dict, user_number: str) -> dict:
    if ("number" not in tool_args) or ("@c.us" not in str(tool_args["number"])):
        tool_args["number"] = user_number
    tool_args.setdefault("user_number", user_number)
    return tool_args


# ── routes ──────────────────────────────────────────────────
@app.get("/ping")
async def ping():
    return {"status": "ok"}


@app.post("/incoming")
async def incoming_whatsapp_message(request: Request):
    payload = await request.json()
    print("📩 Incoming payload:", payload)

    extracted = receive_whatsapp_message(payload)
    if "error" in extracted:
        return {"status": "error", "details": extracted["error"]}

    user_message = extracted["user_message"].strip()
    user_number = extracted["user_number"]

    bookings = load_bookings()
    user_memory = get_user_memory(user_number)

    # — handle a pending “awaiting_email” state —
    if bookings.get(user_number, {}).get("awaiting_email"):
        if "skip" in user_message.lower():
            bookings[user_number]["awaiting_email"] = False
            save_all_bookings(bookings)
            SendWhatsappMsg.invoke(
                {
                    "number": user_number,
                    "message": "👍 No problem – WhatsApp reminders only.",
                }
            )
            return {"status": "email skipped"}

        # super-naïve email regex
        if re.fullmatch(r"[^@\\s]+@[^@\\s]+\\.[^@\\s]+", user_message):
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

        # otherwise ask again
        SendWhatsappMsg.invoke(
            {
                "number": user_number,
                "message": "⚠️ That doesn’t look like an email. "
                "Send a valid address or say 'skip'.",
            }
        )
        return {"status": "awaiting valid email"}

    intent = classify_intent(user_message)
    print(f"🔎 Detected intent: {intent.name}")

    # ── auto-exit booking if user changed topic ────────────────────────
    if is_waiting_for_booking(user_number, bookings) and intent is Intent.OTHER:
        # stay in booking only if they sent a menu number (1-5) or a time string
        if not re.search(r"\b[1-5]\b", user_message) and not re.search(
            r"\d{1,2}[:\.]?\d{0,2}\s*(am|pm)?", user_message, re.I
        ):
            set_waiting_for_booking(user_number, bookings, False)
            save_all_bookings(bookings)

    # ── cancel ───────────────────────────────────────────────
    if intent is Intent.CANCEL_APPT:
        msg = (
            "✅ Your appointment has been canceled."
            if cancel_booking(user_number)
            else "⚠️ You don’t have any appointment to cancel."
        )
        SendWhatsappMsg.invoke({"number": user_number, "message": msg})
        return {"status": "cancel"}

    # ── lookup ───────────────────────────────────────────────
    if intent is Intent.LOOKUP_APPT:
        slot = get_user_booking(user_number)
        msg = (
            f"📅 You are booked for {slot}!"
            if slot
            else "😔 I couldn’t find an active booking for you."
        )
        SendWhatsappMsg.invoke({"number": user_number, "message": msg})
        return {"status": "lookup"}

    # ── mid-booking flow ─────────────────────────────────────
    if is_waiting_for_booking(user_number, bookings):

        # ✱ NEW: allow “Wednesday 3:45” etc. instead of a menu number
        natural = _parse_natural_slot(user_message)
        if natural:
            if slot_taken(natural, exclude_user=user_number):
                SendWhatsappMsg.invoke(
                    {
                        "number": user_number,
                        "message": "⚠️ Sorry, that time was just booked. Please choose another slot.",
                    }
                )
                return {"status": "slot collision"}
            save_individual_booking(user_number, natural)
            SendWhatsappMsg.invoke(
                {
                    "number": user_number,
                    "message": f"✅ You're booked for {natural}! We'll remind you 24 h before.",
                }
            )
            set_waiting_for_booking(user_number, bookings, False)
            b = load_bookings()
            if not b[user_number].get("email"):
                SendWhatsappMsg.invoke(
                    {
                        "number": user_number,
                        "message": "📧 Got an email address? I can also send handy reminders there (optional). "
                        "Just reply with it, or say 'skip'.",
                    }
                )
                # flag so we know the next incoming message should be treated as email
                b[user_number]["awaiting_email"] = True
                save_all_bookings(b)
                return {"status": "ask email"}
            save_all_bookings(bookings)
            return {"status": "confirmed"}

        if result == "slot_taken":
            SendWhatsappMsg.invoke(
                {
                    "number": user_number,
                    "message": "⚠️ Sorry, that time was just booked. Please choose another slot.",
                }
            )
            return {"status": "slot collision"}

        if result == "ask_day":
            SendWhatsappMsg.invoke(
                {
                    "number": user_number,
                    "message": "📅 Sure! Which day would you like an appointment?",
                }
            )
            return {"status": "ask day"}

        if result.startswith("offer::"):
            slots = result.split("::", 1)[1]
            SendWhatsappMsg.invoke(
                {"number": user_number, "message": f"🔎 Available times:\n{slots}"}
            )
            return {"status": "offer"}

        SendWhatsappMsg.invoke(
            {
                "number": user_number,
                "message": "⚠️ Please reply with a number from the list or ask for a different day!",
            }
        )
        return {"status": "waiting"}

    # ── natural-language first contact ───────────────────────
    # ── attempt direct booking with BookingTool before showing a menu ──────────
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
            return {"status": "booked via natural"}

        if result == "slot_taken":
            SendWhatsappMsg.invoke(
                {
                    "number": user_number,
                    "message": "⚠️ Sorry, that time was just booked. Please choose another slot.",
                }
            )
            return {"status": "slot collision"}

    # if result was "unrecognized" we just fall through to the menu branch

    # ── menu presentation (new booking) ──────────────────────
    if intent in {Intent.BOOK_APPT, Intent.CHECK_DAY}:
        requested_day = (
            detect_day_request(user_message) if intent is Intent.CHECK_DAY else ""
        )
        menu_slots = get_booking_options(desired_day=requested_day, raw=True)[:5]
        if not menu_slots:
            SendWhatsappMsg.invoke(
                {"number": user_number, "message": "⚠️ No available slots for that day."}
            )
            return {"status": "no slots"}

        user_shown_slots[user_number] = menu_slots
        set_waiting_for_booking(user_number, bookings, True)
        save_all_bookings(bookings)
        msg = "🔎 Available times:\n" + "\n".join(
            f"{i+1}. {s}" for i, s in enumerate(menu_slots)
        )
        SendWhatsappMsg.invoke({"number": user_number, "message": msg})
        return {"status": "menu"}

    # ── fallback to LLM agent ─────────────────────────────────
    print(f"🤖 Passing to agent: {user_message}")
    tool_name, tool_args = agent.think_llm(user_message)
    tool_args = fill_user_number(tool_args, user_number)
    agent.act(tool_name, tool_args)

    user_memory["last_topic"] = user_message
    save_user_memory(user_number, user_memory)
    return {"status": "agent"}


# ---- dynamic port helper ---------------------------------------------------
def find_open_port(start=8001):
    port = start
    while port < start + 20:
        try:
            with socket.socket() as s:
                s.bind(("", port))
                return port
        except OSError:
            port += 1
    raise OSError("No free ports")


chosen_port = find_open_port()
with open("fastapi_port.txt", "w") as f:
    f.write(str(chosen_port))
print(f"🚀 FastAPI server starting on port {chosen_port}")

if __name__ == "__main__":
    uvicorn.run("src.receiver:app", host="0.0.0.0", port=chosen_port, reload=True)
