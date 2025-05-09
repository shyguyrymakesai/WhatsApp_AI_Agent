# src/routers/fallback.py
from fastapi import APIRouter, Request
from agent.agent import Agent
from tools.whatsapp_snd_tool import SendWhatsappMsg

router = APIRouter()
agent = Agent()


@router.post("/incoming")
async def handle_fallback(request: Request):
    payload = await request.json()
    user_message = payload.get("message", "").strip()
    user_number = payload.get("number", "")
    tool_name, tool_args = agent.think_llm(user_message)

    if tool_name is None or tool_args is None:
        return {"status": "no_action"}

    # ensure the number is set
    tool_args.setdefault("number", user_number)
    tool_args.setdefault("user_number", user_number)

    agent.act(tool_name, tool_args)
    return {"status": "delegated"}
