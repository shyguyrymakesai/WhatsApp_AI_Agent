from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain.tools import Tool
from langchain.tools import StructuredTool
import requests
import tools
from tools.whatsapp_snd_tool import SendWhatsappMsg
from tools.time_tool import GetTime


load_dotenv()

llm = ChatOllama(model="qwen2.5")


class BaseResponse(BaseModel):
    time: str
    main_message: str
    questions_for_user: list[str]
    agentic_tools_used: list[str]
    delivery_status: str

    # Misc (want to be optional)


## Fill out later
class FinancialUpdateRepsonse(BaseModel):
    time: str
    bills_due: list[str]


'''

tools_lst = [
    SendWhatsappMsg,
    GetTime
    ]

parser = PydanticOutputParser(pydantic_object=BaseResponse)

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system", 
            """
            You are an AI Agent that will be helping me test and improve the code for my AI Agent's in general and also yourself!
            Please, answer/execute the user query and use necessary tools. 
            Wrap the output in this format and provide no other text\n{format_instructions}
            """,
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{query}"),
        ("placeholder", "{agent_scratchpad}"),


    ]
).partial(format_instructions = parser.get_format_instructions())

agent = create_tool_calling_agent(
    llm = llm,
    prompt = prompt,
    tools = tools_lst
) 



agent_executor = AgentExecutor(agent = agent, tools = tools_lst, verbose= True)
#msg format is [number : number, msg : msg]
raw_response = agent_executor.invoke({"query": "Hey agent, please send thru whatsapp.  [number: 17655809531, msg: You are so sexy when you are interested, even if pretending, in things i like :)]. "})

try:
    structured_response = parser.parse(raw_response.get("output")[0]["text"])
    print(structured_response)
except Exception as e:
    print("Error parsing response", e, "Raw Response - ", raw_response)


    '''

# main.py

from agent import Agent
from tools.whatsapp_snd_tool import SendWhatsappMsg
from tools.time_tool import GetTime

# Initialize agent
agent = Agent(tools=[SendWhatsappMsg, GetTime])

# Simulate incoming message
incoming_msg = input("📩 Incoming WhatsApp Message: ")

# Agent thinks about it
tool_name, tool_args = agent.think(incoming_msg)

# Agent acts
agent.act(tool_name, tool_args)
