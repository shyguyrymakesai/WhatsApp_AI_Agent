# agent.py
import json
from ollama import Client


class Agent:
    def __init__(self, tools):
        self.tools = tools

    def think(self, user_message):
        """
        SUPER basic rule-based thinking (legacy fallback).
        """
        if "price" in user_message.lower():
            return "SendWhatsappMsg", {
                "number": "+1234567890",  # <-- Later: make dynamic
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
        Ask the local LLM (through Ollama) to decide what to do based on the user's message.
        """
        system_prompt = """You are an intelligent agent that assists customers via WhatsApp.
You are REQUIRED to use the available tools to respond to ANY business-related customer inquiry.

Always prefer using the tool:
- SendWhatsappMsg (requires 'number' and 'message' fields)

RULES:
- If the user asks about services, hours, pricing, scheduling, quotes, help, or anything remotely related to business — you MUST use SendWhatsappMsg.
- You should ASSUME a reply is needed unless the message is absolute spam or junk.
- You should NEVER respond with "no action needed" for service-related questions.
- Always output STRICT JSON. No extra text.

Example when replying:
{
    "tool": "SendWhatsappMsg",
    "args": {
        "number": "+1234567890",
        "message": "Thank you for contacting us! We offer website design, SEO services, and digital marketing solutions."
    }
}

Example only if clear spam:
{
    "tool": null,
    "args": null
}

**Use a tool whenever reasonable doubt exists.**
"""

        client = Client(host="http://localhost:11434")

        response = client.chat(
            model="qwen2.5",  # Change if you want to test other models
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
        Find and use the correct tool.
        """
        if tool_name is None:
            print("🤖 Agent: No action needed.")
            return

        for tool in self.tools:
            if tool.name == tool_name:
                print(f"🤖 Agent: Invoking tool {tool_name} with args {tool_args}")
                return tool.invoke(tool_args)

        print(f"⚠️ Agent: Tool {tool_name} not found.")
