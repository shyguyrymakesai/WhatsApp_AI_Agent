from fastapi import FastAPI, Request
import uvicorn

from agent.agent import Agent
from tools.whatsapp_snd_tool import SendWhatsappMsg
from tools.whatsapp_rcv_tool import receive_whatsapp_message
from handlers.booking_handler import (
    initialize_bookings_file,
    detect_booking_intent,
    detect_cancel_intent,
    get_booking_options,
    handle_booking_response,
    cancel_booking,
    load_bookings,
    save_bookings,
    is_valid_booking_option,
    is_waiting_for_booking,
    set_waiting_for_booking,
)
from handlers.day_detector import detect_day_request  # (I'll explain this one in a sec)


# Initialize app
app = FastAPI()

# Initialize agent
agent = Agent(tools=[SendWhatsappMsg])

# Initialize bookings
initialize_bookings_file()


# --- Helper functions ---

# receiver.py
DAYS_OF_WEEK = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


def detect_day_request(message: str) -> str:
    message = message.lower()
    for day in DAYS_OF_WEEK:
        if day in message:
            return day
    return ""


def count_current_booking_options() -> int:
    """
    Dynamically count how many booking slots are currently being offered.
    """
    options_message = get_booking_options()
    return options_message.count("🕒")


def is_valid_booking_option(message: str) -> bool:
    """
    Check if the user replied with a valid booking option number.
    """
    if not message.isdigit():
        return False

    max_option = count_current_booking_options()
    selection = int(message)

    return 1 <= selection <= max_option


# -------------------------


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

    # Check if user is supposed to be choosing a time
    waiting_for_slot = is_waiting_for_booking(user_number, bookings)

    # Always allow cancellation first
    if detect_cancel_intent(user_message):
        if cancel_booking(user_number):
            SendWhatsappMsg.invoke(
                input={
                    "number": user_number,
                    "message": "✅ Your appointment has been canceled. Feel free to book a new time anytime!",
                }
            )
        else:
            SendWhatsappMsg.invoke(
                input={
                    "number": user_number,
                    "message": "⚠️ No active booking found under your number.",
                }
            )
        return {"status": "cancelation handled"}

    # If waiting for slot, expect a number
    if waiting_for_slot:
        if is_valid_booking_option(user_message.strip()):
            booking_response = handle_booking_response(user_number, user_message)
            set_waiting_for_booking(user_number, bookings, False)
            save_bookings(bookings)
            SendWhatsappMsg.invoke(
                input={"number": user_number, "message": booking_response}
            )
            return {"status": "booking confirmed"}
        else:
            SendWhatsappMsg.invoke(
                input={
                    "number": user_number,
                    "message": "⚠️ Please reply with a number from the list to confirm your appointment.",
                }
            )
            return {"status": "awaiting valid booking reply"}

    # Detect request for different day
    requested_day = detect_day_request(user_message)
    if requested_day and requested_day != "monday":
        SendWhatsappMsg.invoke(
            input={
                "number": user_number,
                "message": "⚠️ Sorry, we currently only offer Monday appointments right now.",
            }
        )
        return {"status": "unsupported day"}

    # Detect booking intent ONLY if no booking exists
    if detect_booking_intent(user_message) and user_number not in bookings:
        booking_options = get_booking_options()
        set_waiting_for_booking(user_number, bookings, True)
        save_bookings(bookings)
        SendWhatsappMsg.invoke(
            input={"number": user_number, "message": booking_options}
        )
        return {"status": "booking options sent"}

    # Otherwise use agent for chatting
    tool_name, tool_args = agent.think_llm(user_message)

    if tool_args and "number" in tool_args:
        tool_args["number"] = user_number

    agent.act(tool_name, tool_args)

    return {"status": "success"}


if __name__ == "__main__":
    uvicorn.run("receiver:app", host="0.0.0.0", port=8000, reload=True)
