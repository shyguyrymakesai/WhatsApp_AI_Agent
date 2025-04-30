# agent/agent.py – patched
import json
from pathlib import Path

from ollama import Client

from src.tools.whatsapp_snd_tool import SendWhatsappMsg
from src.tools.booking_tool import BookingTool
from src.tools.time_tool import GetTime
from src.tools.check_booking_tool import CheckBookingTool
from src.tools.check_availability_tool import CheckAvailabilityTool


class Agent:
    """LLM-driven decision maker that routes user messages to src.tools."""

    def __init__(self, tools=None):
        self.tools = tools or [
            SendWhatsappMsg,
            GetTime,
            BookingTool,
            CheckBookingTool,
            CheckAvailabilityTool,
        ]

    # ---------------------------------------------------------------------
    # LLM "think" step -----------------------------------------------------
    # ---------------------------------------------------------------------
    def think_llm(self, user_message: str):
        """Ask the local Ollama LLM what tool + args to run."""
        STYLE_SHIM = (
            "Always sound friendly and concise; sprinkle an emoji only "
            "when it adds warmth (e.g., ✅, 😊)."
        )

        system_prompt = (
            STYLE_SHIM
            + "\n"
            + """You are an intelligent agent that assists customers via WhatsApp.
You are REQUIRED to use the available tools to respond to ANY business-related customer inquiry.

Available tools:
- SendWhatsappMsg (requires 'number' and 'message')
- BookingTool (requires 'user_message' and 'user_number')
- CheckBookingTool (requires 'user_number')
- CheckAvailabilityTool (requires 'slot' and 'user_number')

RULES:
- If the user asks about services, hours, pricing, scheduling, booking, appointments, quotes, help, or anything remotely related to business — you MUST use a tool.
- Never answer directly without using a tool.
- Always output STRICT JSON like:
{
  "tool": "ToolName",
  "args": { "field1": "value", "field2": "value" }
}
- “If the user asks whether a specific day-time is free, call CheckAvailabilityTool first.
If it returns available, immediately book it with BookingTool.”

If unsure, default to SendWhatsappMsg.
ONLY skip action if the message is clear spam.
"""
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
        print("\n🛠️ RAW LLM RESPONSE:")
        print(response_text)

        try:
            parsed = json.loads(response_text)
            return parsed["tool"], parsed["args"]
        except Exception as e:
            print(f"⚠️ Agent: Failed to parse LLM output: {e}")
            return None, None

    # ---------------------------------------------------------------------
    # "Act" step: invoke the chosen tool and optionally relay its output ----
    # ---------------------------------------------------------------------
    def act(self, tool_name: str | None, tool_args: dict | None):
        if tool_name is None or tool_args is None:
            print("🤖 Agent: No action needed.")
            return None

        # Ensure WhatsApp JID present
        if "number" not in tool_args or "@c.us" not in str(tool_args.get("number", "")):
            # Fall back to user_number if provided
            if user := tool_args.get("user_number"):
                tool_args["number"] = user

        normalized = tool_name.lower()

        for tool in self.tools:
            print(f"🔍 Available tool: {tool.name}")
            if tool.name.lower() == normalized:
                print(f"🤖 Agent: Invoking tool {tool.name} with args {tool_args}")
                result = tool.invoke(tool_args)

                # 🔄 If the tool just returns a message, forward it to WhatsApp
                if isinstance(result, str) and result.strip():
                    SendWhatsappMsg.invoke(
                        {
                            "number": tool_args.get(
                                "number", tool_args.get("user_number")
                            ),
                            "message": result.strip(),
                        }
                    )
                    return result

                # ----- Auto-relay Booking / Check responses -------------
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
                return result

        print(f"⚠️ Agent: Tool {tool_name} not found.")
        return None

    # ------------------------------------------------------------------
    # Helpers -----------------------------------------------------------
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_booking_response(raw: str) -> str:
        """Convert BookingTool status strings into user-friendly messages."""
        if raw.startswith("offer::"):
            return "🔎 Available times:\n" + raw.split("::", 1)[1]
        if raw.startswith("booked::"):
            return f"✅ You're booked for {raw.split('::', 1)[1]}! We'll remind you 24 h before."
        if raw == "ask_day":
            return "📅 Sure! Which day would you like an appointment?"
        if raw == "slot_taken":
            return "⚠️ Sorry, that time was just booked. Please choose another slot."
        if raw == "available":
            return "✅ Great news — that time is free! Booking it now…"
        if raw.startswith("nearest::"):
            return "⚠️ That slot is taken. Nearest available is " + raw.split("::", 1)[1]
        if raw == "taken":
            return "⚠️ Sorry, that day is fully booked. Pick another time."
        return raw  # pass through if already friendly
