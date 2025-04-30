# src/memory/memory_client.py
import requests

MCP_BASE_URL = "http://localhost:9000"


def get_user_memory(user_id: str) -> dict:
    response = requests.get(f"{MCP_BASE_URL}/memory/{user_id}")
    if response.status_code == 200:
        return response.json()
    return {}


def save_user_memory(user_id: str, memory: dict):
    response = requests.post(
        f"{MCP_BASE_URL}/memory/{user_id}", json={"memory": memory}
    )
    return response.json()


def delete_user_memory(user_id: str):
    response = requests.delete(f"{MCP_BASE_URL}/memory/{user_id}")
    return response.json()
