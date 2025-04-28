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
)

# Initialize app
app = FastAPI()

# Initialize agent
agent = Agent(tools=[SendWhatsappMsg])

# Initialize bookings
initialize_bookings_file()


# --- Helper functions ---
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

    # Detect cancel intent
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

    # Detect booking intent
    if detect_booking_intent(user_message):
        booking_options = get_booking_options()
        SendWhatsappMsg.invoke(
            input={"number": user_number, "message": booking_options}
        )
        return {"status": "booking options sent"}

    # Handle number reply
    if is_valid_booking_option(user_message.strip()):
        booking_response = handle_booking_response(user_number, user_message)
        SendWhatsappMsg.invoke(
            input={"number": user_number, "message": booking_response}
        )
        return {"status": "booking confirmed"}

    # Otherwise use agent to handle
    tool_name, tool_args = agent.think_llm(user_message)

    if tool_args and "number" in tool_args:
        tool_args["number"] = user_number

    agent.act(tool_name, tool_args)

    return {"status": "success"}


if __name__ == "__main__":
    uvicorn.run("receiver:app", host="0.0.0.0", port=8000, reload=True)
