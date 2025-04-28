from fastapi import FastAPI, Request
import uvicorn
import re
from collections import defaultdict

from agent.agent import Agent
from tools.whatsapp_snd_tool import SendWhatsappMsg
from tools.whatsapp_rcv_tool import receive_whatsapp_message
from tools.booking_tool import BookingTool
from tools.time_tool import GetTime
from handlers.booking_handler import (
    initialize_bookings_file,
    detect_booking_intent,
    detect_cancel_intent,
    get_booking_options,
    handle_booking_response,
    cancel_booking,
    load_bookings,
    save_all_bookings,
    save_individual_booking,
    is_valid_booking_option,
    is_waiting_for_booking,
    set_waiting_for_booking,
)
from handlers.day_detector import detect_day_request

# ---------------------- Setup ----------------------

# Track booking slots shown to each user
user_shown_slots = defaultdict(list)

app = FastAPI()
agent = Agent(tools=[SendWhatsappMsg, GetTime, BookingTool])
initialize_bookings_file()

DAYS_OF_WEEK = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]

# ------------------- Helper Functions -------------------


def extract_number_from_message(message: str) -> int:
    match = re.search(r"\b(\d+)\b", message)
    return int(match.group(1)) if match else -1


def fill_user_number(tool_args: dict, user_number: str) -> dict:
    if not tool_args.get("number"):
        tool_args["number"] = user_number
    if not tool_args.get("user_number"):
        tool_args["user_number"] = user_number
    return tool_args


# --------------------- Routes ------------------------


@app.post("/incoming")
async def incoming_whatsapp_message(request: Request):
    payload = await request.json()
    print("📩 Incoming payload:", payload)

    extracted = receive_whatsapp_message(payload)
    if "error" in extracted:
        return {"status": "error", "details": extracted["error"]}

    user_message = extracted["user_message"]
    user_number = extracted["user_number"]
    bookings = load_bookings()

    # --- 1. Cancellation ---
    if detect_cancel_intent(user_message):
        if cancel_booking(user_number):
            SendWhatsappMsg.invoke(
                input={
                    "number": user_number,
                    "message": "✅ Your appointment has been canceled.",
                }
            )
        else:
            SendWhatsappMsg.invoke(
                input={"number": user_number, "message": "⚠️ No active booking found."}
            )
        return {"status": "cancellation handled"}

    # --- 2. Existing booking flow ---
    if is_waiting_for_booking(user_number, bookings):
        selection = extract_number_from_message(user_message)
        if 1 <= selection <= len(user_shown_slots[user_number]):
            selected_slot = user_shown_slots[user_number][selection - 1]
            booking_response = handle_booking_response(
                user_number, user_message, user_shown_slots
            )

            set_waiting_for_booking(user_number, bookings, False)
            save_all_bookings(bookings)
            SendWhatsappMsg.invoke(
                input={"number": user_number, "message": booking_response}
            )
            return {"status": "booking confirmed"}

        requested_day = detect_day_request(user_message)
        if requested_day:
            new_slots = get_booking_options(desired_day=requested_day, raw=True)
            if not new_slots:
                SendWhatsappMsg.invoke(
                    input={
                        "number": user_number,
                        "message": "⚠️ No available slots for that day.",
                    }
                )
                return {"status": "no slots for requested day"}

            user_shown_slots[user_number] = new_slots
            options_message = "🔎 Available times:\n" + "\n".join(
                [f"{i+1}. {slot}" for i, slot in enumerate(new_slots)]
            )
            SendWhatsappMsg.invoke(
                input={"number": user_number, "message": options_message}
            )
            return {"status": "updated booking options"}

        SendWhatsappMsg.invoke(
            input={
                "number": user_number,
                "message": "⚠️ Please reply with a number from the list or ask for a different day!",
            }
        )
        return {"status": "awaiting valid booking reply"}

    # --- 3. New booking intent ---
    if detect_booking_intent(user_message):
        slots = get_booking_options(raw=True)
        if not slots:
            SendWhatsappMsg.invoke(
                input={"number": user_number, "message": "⚠️ No available slots found."}
            )
            return {"status": "no slots available"}

        user_shown_slots[user_number] = slots
        options_message = "🔎 Available times:\n" + "\n".join(
            [f"{i+1}. {slot}" for i, slot in enumerate(slots)]
        )

        set_waiting_for_booking(user_number, bookings, True)
        save_all_bookings(bookings)
        SendWhatsappMsg.invoke(
            input={"number": user_number, "message": options_message}
        )
        return {"status": "booking options sent"}

    # --- 4. Pass to agent (LLM fallback) ---
    print(f"🤖 Passing to agent: {user_message}")
    tool_name, tool_args = agent.think_llm(user_message)
    print(f"🧠 Agent decided: tool_name={tool_name}, tool_args={tool_args}")

    if tool_args:
        tool_args = fill_user_number(tool_args, user_number)

    agent.act(tool_name, tool_args)
    return {"status": "success"}


# ---------------------- Run ------------------------

if __name__ == "__main__":
    uvicorn.run("receiver:app", host="0.0.0.0", port=8000, reload=True)
