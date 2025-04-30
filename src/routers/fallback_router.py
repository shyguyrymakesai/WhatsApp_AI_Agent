# src/routers/fallback.py
from fastapi import APIRouter, Request
from agent.agent import Agent

router = APIRouter()
agent = Agent()


@router.post("/")
async def handle_fallback(request: Request):
    payload = await request.json()
    user_message = payload.get("message", "").strip()
    user_number = payload.get("number", "")
    tool_name, tool_args = agent.think_llm(user_message)
    tool_args.setdefault("number", user_number)
    tool_args.setdefault("user_number", user_number)
    agent.act(tool_name, tool_args)
    return {"status": "agent"}
