from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_tool_calling_agent, AgentExecutor
from tools.whatsapp_snd_tool import SendWhatsappMsg
from tools.time_tool import GetTime
from tools.booking_tool import BookingTool
from typing import List
from pydantic import BaseModel
import tools

# Load environment variables
load_dotenv()

# Initialize LLM
llm = ChatOllama(model="qwen2.5")

# Tools
tools_lst = [SendWhatsappMsg, GetTime, BookingTool]


# Structured output model
class BaseResponse(BaseModel):
    time: str
    main_message: str
    questions_for_user: List[str]
    agentic_tools_used: List[str]
    delivery_status: str


# Output parser
parser = PydanticOutputParser(pydantic_object=BaseResponse)

# Prompt
prompt = ChatPromptTemplate.from_messages(
    [
        (
            (
                "system",
                """You are an AI Agent assisting customers on WhatsApp.

RULES:
- ALWAYS use the provided tools to respond.
- ALWAYS use the real customer phone number passed to you. Never invent or guess numbers.
- REPLY using tools even if the user asks casually, unless it is obvious spam.
- NEVER respond directly without using a tool unless you are explicitly told.
- NEVER output extra commentary. Only tool invocation or formatted JSON responses are allowed.

TOOLS AVAILABLE:
- SendWhatsappMsg (fields: number, message)
- GetTime
- BookingTool

If unsure, it's better to attempt a tool than to stay silent.

{format_instructions}
""",
            ),
        ),
        ("human", "{query}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
).partial(format_instructions=parser.get_format_instructions())

# Create agent
agent = create_tool_calling_agent(
    llm=llm,
    prompt=prompt,
    tools=tools_lst,
)

# Executor
agent_executor = AgentExecutor(agent=agent, tools=tools_lst, verbose=True)

# Example execution
if __name__ == "__main__":
    incoming_msg = input("📩 Incoming WhatsApp Message: ")
    raw_response = agent_executor.invoke({"query": incoming_msg})

    try:
        structured_response = parser.parse(raw_response.get("output")[0]["text"])
        print(structured_response)
    except Exception as e:
        print("Error parsing response:", e)
        print("Raw Response:", raw_response)
