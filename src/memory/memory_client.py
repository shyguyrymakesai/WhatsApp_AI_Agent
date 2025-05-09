# File: src/memory/memory_client.py
import requests

MCP_BASE_URL = "http://localhost:9000"


def get_user_memory(user_id: str) -> dict:
    try:
        resp = requests.get(f"{MCP_BASE_URL}/memory/{user_id}")
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return {}


def save_user_memory(user_id: str, memory: dict) -> dict:
    try:
        resp = requests.post(
            f"{MCP_BASE_URL}/memory/{user_id}",
            json={"memory": memory},
        )
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        return {"error": str(e)}


def delete_user_memory(user_id: str) -> dict:
    try:
        resp = requests.delete(f"{MCP_BASE_URL}/memory/{user_id}")
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        return {"error": str(e)}
