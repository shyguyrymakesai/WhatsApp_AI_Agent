# test_agent.py

from src.agent.agent import Agent
from tools.whatsapp_snd_tool import SendWhatsappMsg
from tools import GetTime
from tools import BookingTool

# Initialize agent
agent = Agent(tools=[SendWhatsappMsg, GetTime, BookingTool])

# List of fake incoming WhatsApp messages to stress test the agent
test_messages = [
    "Hi, how much do your services cost?",
    "When are you open?",
    "Where is your office located?",
    "What services do you provide?",
    "How can I contact you for a quote?",
    "Do you offer social media marketing?",
    "What are your business hours on weekends?",
    "Can I get your email address?",
    "I'd like to book a consultation.",
    "Thank you for your help!",
]

for idx, msg in enumerate(test_messages, start=1):
    print(f"\n📩 Test {idx}: {msg}")
    tool_name, tool_args = agent.think_llm(msg)
    agent.act(tool_name, tool_args)
