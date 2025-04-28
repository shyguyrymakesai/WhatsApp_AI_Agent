# agent/agent.py
import json
from ollama import Client
from tools.whatsapp_snd_tool import SendWhatsappMsg
from tools.booking_tool import BookingTool
from tools.time_tool import GetTime


class Agent:
    def __init__(self, tools=None):
        if tools is None:
            tools = [SendWhatsappMsg, GetTime, BookingTool]

        self.tools = tools

    def think(self, user_message):
        """
        SUPER basic rule-based thinking (legacy fallback).
        """
        if "price" in user_message.lower():
            return "SendWhatsappMsg", {
                "number": "+1234567890",
                "message": "Our services start at $99/month!",
            }
        elif "hours" in user_message.lower():
            return "SendWhatsappMsg", {
                "number": "+1234567890",
                "message": "We are open Monday to Friday, 9am to 6pm.",
            }
        else:
            return None, None

    def think_llm(self, user_message):
        """
        Ask local LLM via Ollama to decide action.
        """
        system_prompt = """You are an intelligent agent that assists customers via WhatsApp.
You are REQUIRED to use the available tools to respond to ANY business-related customer inquiry.

Available tools:
- SendWhatsappMsg (requires 'number' and 'message')
- BookingTool (requires 'user_message' and 'user_number')

RULES:
- If the user asks about services, hours, pricing, scheduling, booking, appointments, quotes, help, or anything remotely related to business — you MUST use a tool.
- Never answer directly without using a tool.
- Always output STRICT JSON like:

{
    "tool": "ToolName",
    "args": { "field1": "value", "field2": "value" }
}

If unsure, default to SendWhatsappMsg.

ONLY skip action if the message is clear spam.
"""

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

    def act(self, tool_name, tool_args):
        """
        Find and use the correct tool, ensuring 'number' field is set correctly.
        """
        if tool_name is None:
            print("🤖 Agent: No action needed.")
            return

        # Ensure 'number' is correctly set
        if "user_number" in tool_args and "number" not in tool_args:
            tool_args["number"] = tool_args["user_number"]  # Fix for missing 'number'

        normalized_tool_name = tool_name.lower()

        for tool in self.tools:
            print(f"🔍 Available tool: {tool.name}")  # still helpful
            if tool.name.lower() == normalized_tool_name:
                print(f"🤖 Agent: Invoking tool {tool.name} with args {tool_args}")
                return tool.invoke(tool_args)

        print(f"⚠️ Agent: Tool {tool_name} not found.")
