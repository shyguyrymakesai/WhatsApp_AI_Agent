# src/agent/agent.py
import json
from datetime import datetime
from ollama import Client
from src.tools.whatsapp_snd_tool import SendWhatsappMsg
from src.tools.booking_tool import BookingTool
from src.tools.time_tool import GetTime
from src.tools.check_booking_tool import CheckBookingTool
from src.tools.check_availability_tool import CheckAvailabilityTool
from src.memory.memory_client import get_user_memory, save_user_memory


class Agent:
    """LLM-driven decision maker that routes user messages to src.tools and uses MCP for memory."""

    def __init__(self, user_id: str, tools=None):
        self.user_id = user_id
        self.tools = tools or [
            SendWhatsappMsg,
            GetTime,
            BookingTool,
            CheckBookingTool,
            CheckAvailabilityTool,
        ]

    def think_llm(self, user_message: str):
        """Ask the local Ollama LLM what tool + args to run, including memory context."""
        # Load user memory
        user_mem = get_user_memory(self.user_id) or {}
        # Build memory block for prompt
        mem_lines = []
        # Identity & contact
        if "email" in user_mem:
            mem_lines.append(f"Email: {user_mem['email']}")
        if "phone_number" in user_mem:
            mem_lines.append(f"Phone: {user_mem['phone_number']}")
        if "timezone" in user_mem:
            mem_lines.append(f"Timezone: {user_mem['timezone']}")
        # Bookings
        for b in user_mem.get("upcoming_bookings", []):
            mem_lines.append(f"Upcoming booking: {b}")
        # Preferences
        if "preferred_services" in user_mem:
            mem_lines.append(
                f"Preferred services: {', '.join(user_mem['preferred_services'])}"
            )
        # Session context
        if "last_message" in user_mem:
            mem_lines.append(f"Last message: {user_mem['last_message']}")
        if "awaiting_response_for" in user_mem:
            mem_lines.append(f"Awaiting: {user_mem['awaiting_response_for']}")
        # Behavior
        if "message_count" in user_mem:
            mem_lines.append(f"Messages so far: {user_mem['message_count']}")
        # Combine into block
        mem_block = (
            (
                "Previous memory:\n"
                + "\n".join(f"- {line}" for line in mem_lines)
                + "\n\n"
            )
            if mem_lines
            else ""
        )

        STYLE_SHIM = (
            "Always sound friendly and concise; sprinkle an emoji only "
            "when it adds warmth (e.g., ✅, 😊)."
        )
        system_prompt = (
            STYLE_SHIM
            + "\n"
            + mem_block
            + """You are an intelligent agent named Bob that assists customers via WhatsApp."
"Use the available tools to respond to every business-related inquiry, routing through tool calls as needed."
"Only respond in JSON specifying 'tool' and 'args'."""
        )

        client = Client(host="http://localhost:11434")
        response = client.chat(
            model="qwen2.5",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"User message: {user_message}"},
            ],
        )
        response_text = response["message"]["content"]
        print("\n🛠️ RAW LLM RESPONSE:\n", response_text)

        try:
            parsed = json.loads(response_text)
            return parsed.get("tool"), parsed.get("args") or {}
        except Exception as e:
            print(f"⚠️ Agent: Failed to parse LLM output: {e}")
            return None, None

    def act(self, tool_name: str | None, tool_args: dict | None, user_message: str):
        """Invoke the chosen tool, relay results, and save updated memory."""
        # Load and prepare memory update
        user_mem = get_user_memory(self.user_id) or {}
        user_mem["last_message"] = user_message
        user_mem["message_count"] = user_mem.get("message_count", 0) + 1
        user_mem["last_interaction_ts"] = datetime.utcnow().isoformat()

        if tool_name is None or tool_args is None:
            print("🤖 Agent: No action needed.")
            save_user_memory(self.user_id, user_mem)
            return None

        # Ensure WhatsApp JID present
        if "number" not in tool_args or "@c.us" not in str(tool_args.get("number", "")):
            if user := tool_args.get("user_number"):
                tool_args["number"] = user

        # Capture contact info
        if "email" in tool_args:
            user_mem["email"] = tool_args["email"]
        if "number" in tool_args:
            user_mem["phone_number"] = tool_args["number"]

        normalized = tool_name.lower()
        result = None

        for tool in self.tools:
            if tool.name.lower() == normalized:
                print(f"🤖 Agent: Invoking tool {tool.name} with args {tool_args}")
                result = tool.invoke(tool_args)
                # Handle direct string replies
                if isinstance(result, str) and result.strip():
                    SendWhatsappMsg.invoke(
                        {
                            "number": tool_args["number"],
                            "message": result.strip(),
                        }
                    )
                    result_text = result.strip()
                # Booking tool normalization and memory update
                if tool.name in {"BookingTool", "CheckBookingTool"} and isinstance(
                    result, str
                ):
                    msg = self._normalize_booking_response(result)
                    SendWhatsappMsg.invoke(
                        {
                            "number": tool_args["number"],
                            "message": msg,
                        }
                    )
                    # On new booking, record slot
                    if tool.name == "BookingTool" and result.startswith("booked::"):
                        slot = result.split("::", 1)[1]
                        upcoming = user_mem.get("upcoming_bookings", [])
                        upcoming.append({"slot": slot})
                        user_mem["upcoming_bookings"] = upcoming
                break

        if result is None:
            print(f"⚠️ Agent: Tool {tool_name} not found.")

        # Persist memory
        save_user_memory(self.user_id, user_mem)
        return result

    @staticmethod
    def _normalize_booking_response(raw: str) -> str:
        """Convert BookingTool status strings into user-friendly messages."""
        if raw.startswith("offer::"):
            return "🔎 Available times:\n" + raw.split("::", 1)[1]
        if raw.startswith("booked::"):
            return f"✅ You're booked for {raw.split('::',1)[1]}! We'll remind you 24 h before."
        if raw == "ask_day":
            return "📅 Which day would you like?"
        if raw == "slot_taken":
            return "⚠️ That time was just booked."
        if raw == "available":
            return "✅ Time is free, booking now…"
        if raw.startswith("nearest::"):
            return "⚠️ Nearest available is " + raw.split("::", 1)[1]
        return raw
