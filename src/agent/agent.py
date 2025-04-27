# agent.py
import json
from ollama import Client


class Agent:
    def __init__(self, tools):
        self.tools = tools

    def think(self, user_message):
        """
        Decide what tool to use based on the user's message.
        """
        # SUPER basic rule-based thinking for now
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
        prompt = f"""
        You are an AI agent helping a small business manage WhatsApp messages.

        Your job is to always decide if a tool should be used based on the user's message.

        Available Tool:
        - SendWhatsappMsg (requires 'number' and 'message' fields)

        Incoming Message: "{user_message}"

        Instructions:
        - If the user's message seems like a question, inquiry, request, or anything related to business services, assume they need a reply.
        - Only respond with pure JSON format, no extra text.
        - If possible, prefer using the available tool to help the user.
        - Use this exact format:

        {{
            "tool": "SendWhatsappMsg",
            "args": {{
                "number": "+1234567890",
                "message": "Reply message here."
            }}
        }}

        - If you are absolutely sure the message is just casual or unrelated, you may reply with:

        {{
            "tool": null,
            "args": null
        }}

        STRICT FORMAT ONLY. No explanations. No extra sentences. Only pure JSON.
        """

        # Initialize Ollama client
        client = Client(host="http://localhost:11434")

        # Send prompt to your local model (adjust model name as needed)
        response = client.chat(
            model="qwen2.5",  # <-- or "llama3", or whatever you want
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract response text
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
