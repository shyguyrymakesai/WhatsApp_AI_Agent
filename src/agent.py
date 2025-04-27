# agent.py

class Agent:
    def __init__(self, tools):
        self.tools = tools

    def think(self, user_message):
        """
        Decide what tool to use based on the user's message.
        """
        user_message_lower = user_message.lower()

        # Price inquiries
        if any(keyword in user_message_lower for keyword in ["price", "cost", "rate"]):
            return "SendWhatsappMsg", {
                "number": "+1234567890",  # <- We'll dynamic this later
                "message": "Our services start at $99/month. Let us know if you need more details!"
            }
        
        # Business hours
        if any(keyword in user_message_lower for keyword in ["hours", "open", "time"]):
            return "SendWhatsappMsg", {
                "number": "+1234567890",
                "message": "We are open Monday to Friday, from 9AM to 6PM."
            }

        # Location inquiries
        if any(keyword in user_message_lower for keyword in ["location", "address", "where"]):
            return "SendWhatsappMsg", {
                "number": "+1234567890",
                "message": "Our office is located at 123 Main Street, Springfield."
            }

        # Services offered
        if any(keyword in user_message_lower for keyword in ["services", "offerings"]):
            return "SendWhatsappMsg", {
                "number": "+1234567890",
                "message": "We offer web design, social media marketing, and branding services!"
            }

        # Contact information
        if any(keyword in user_message_lower for keyword in ["contact", "phone", "email"]):
            return "SendWhatsappMsg", {
                "number": "+1234567890",
                "message": "You can reach us at (123) 456-7890 or email hello@example.com!"
            }

        # If no matches, no action
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
