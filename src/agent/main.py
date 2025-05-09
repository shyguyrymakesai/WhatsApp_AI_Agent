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
    return {"tool": tool, "args": args or {}}
