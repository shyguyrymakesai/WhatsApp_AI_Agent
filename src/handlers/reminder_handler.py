from utils.whatsapp import send_whatsapp_message


def handle_reminder(phone_number: str, message: str):
    # TODO: Properly extract reminder time and content
    send_whatsapp_message(
        phone_number,
        "📅 Reminder received! I'll remind you soon. (Saving not implemented yet.)",
    )
