from src.utils.whatsapp import send_whatsapp_message


def handle_question(phone_number: str, message: str):
    # TODO: Query an LLM or knowledge base
    send_whatsapp_message(
        phone_number, "🤔 Let me think about that... (Answering not implemented yet.)"
    )
