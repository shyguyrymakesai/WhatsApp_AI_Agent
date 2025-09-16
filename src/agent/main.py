# src/agent/main.py

from .agent import Agent


def run_agent(prompt: str) -> dict:
    """
    Entrypoint for eval harness:
    - calls your Agent to pick a tool + args
    - returns {"tool": ..., "args": {...}}
    """
    agent = Agent()
    tool, args = agent.think_llm(prompt)
    if not tool:
        tool, args = agent._fallback_tool(prompt, "no tool selected")
    return {"tool": tool, "args": args or {}}
