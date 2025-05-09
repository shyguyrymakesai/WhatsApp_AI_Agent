# src/routers/booking_router.py
import re
from fastapi import APIRouter, Request
from langchain.tools import StructuredTool

from src.handlers.booking_handler import (
    load_bookings,
    save_all_bookings,
    is_waiting_for_booking,
    set_waiting_for_booking,
    get_booking_options,
    save_individual_booking,
    slot_taken,
)
from src.handlers.intent_classifier import classify_intent, Intent
from tools.whatsapp_snd_tool import SendWhatsappMsg
from utils.slot_parser import parse_slot

router = APIRouter()


@router.post("")
async def handle_booking(request: Request):
    payload = await request.json()
    user_message = payload.get("message", "").strip()
    user_number = payload.get("number", "")

    bookings = load_bookings()

    # 1) Mid-booking: try natural-language slot first
    if is_waiting_for_booking(user_number, bookings):
        # a) natural time parse
        natural = parse_slot(user_message)
        if natural:
            if slot_taken(natural, bookings, exclude_user=user_number):
                SendWhatsappMsg.invoke(
                    {
                        "number": user_number,
                        "message": "⚠️ Sorry, that time was just booked. Please choose another slot.",
                    }
                )
                return {"status": "slot_collision"}

            # write the new slot
            save_individual_booking(user_number, natural)

            # re-load so we get that “time” field
            bookings = load_bookings()

            # now clear the waiting flag on the fresh state
            set_waiting_for_booking(user_number, bookings, False)
            save_all_bookings(bookings)

            SendWhatsappMsg.invoke(
                {
                    "number": user_number,
                    "message": f"✅ You're booked for {natural}! We'll remind you 24 h before.",
                }
            )
            return {"status": "booked_natural"}

        # b) numeric menu selection?
        if re.fullmatch(r"[1-5]", user_message):
            index = int(user_message) - 1
            options = get_booking_options(raw=True)[:5]
            try:
                choice = options[index]
            except IndexError:
                # fall through to invalid-reply below
                pass
            else:
                if slot_taken(choice, bookings, exclude_user=user_number):
                    SendWhatsappMsg.invoke(
                        {
                            "number": user_number,
                            "message": "⚠️ That slot was just taken, please pick another.",
                        }
                    )
                    return {"status": "slot_collision"}

                # write the new slot
                save_individual_booking(user_number, natural)

                # re-load so we get that “time” field
                bookings = load_bookings()

                # now clear the waiting flag on the fresh state
                set_waiting_for_booking(user_number, bookings, False)
                save_all_bookings(bookings)

                SendWhatsappMsg.invoke(
                    {
                        "number": user_number,
                        "message": f"✅ You're booked for {choice}! We'll remind you 24 h before.",
                    }
                )
                return {"status": "booked_menu"}

        # c) they've neither given a valid slot nor a menu number → reprompt
        SendWhatsappMsg.invoke(
            {
                "number": user_number,
                "message": "⚠️ Please reply with a number from the list or ask for a different day!",
            }
        )
        return {"status": "awaiting_valid_reply"}

    # 2) Brand-new booking request
    intent = classify_intent(user_message)
    natural = parse_slot(user_message)
    day_only = intent == Intent.CHECK_DAY

    if intent in {Intent.BOOK_APPT, Intent.RESCHEDULE_APPT, Intent.CHECK_DAY}:
        # if they said “reschedule” we may have cleared old booking earlier
        # show the menu (possibly filtered by day)
        desired_day = natural.split()[0] if natural and day_only else ""
        slots = get_booking_options(desired_day=desired_day, raw=True)[:5]
        if not slots:
            SendWhatsappMsg.invoke(
                {
                    "number": user_number,
                    "message": "⚠️ No available slots for that day.",
                }
            )
            return {"status": "no_slots"}

        # save menu state & send top-5
        set_waiting_for_booking(user_number, bookings, True)
        save_all_bookings(bookings)

        menu = "\n".join(f"{i+1}. {s}" for i, s in enumerate(slots))
        SendWhatsappMsg.invoke(
            {
                "number": user_number,
                "message": f"🔎 Available times:\n{menu}",
            }
        )
        return {"status": "menu_shown"}

    # 3) Not a booking intent → fall through
    # (your orchestrator will hand off to LLM agent)
    return {"status": "not_booking"}
