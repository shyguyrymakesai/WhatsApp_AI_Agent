# File: src/memory/mcp_server.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import json

app = FastAPI()

MEMORY_FILE = "data/user_memory.json"


# Ensure memory file exists
def _ensure_memory_file():
    if not os.path.exists(MEMORY_FILE):
        os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
        with open(MEMORY_FILE, "w") as f:
            json.dump({}, f)


_ensure_memory_file()


# Load memory
def load_memory():
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)


# Save memory
def save_memory(memory_data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory_data, f, indent=4)


# Pydantic model for memory payloads
class MemoryPayload(BaseModel):
    memory: dict


@app.get("/memory/{user_id}")
async def get_memory(user_id: str):
    data = load_memory()
    return data.get(user_id, {})


@app.post("/memory/{user_id}")
async def save_user_memory(user_id: str, payload: MemoryPayload):
    data = load_memory()
    data[user_id] = payload.memory
    save_memory(data)
    return {"status": "memory saved"}


@app.delete("/memory/{user_id}")
async def delete_user_memory(user_id: str):
    data = load_memory()
    if user_id in data:
        del data[user_id]
        save_memory(data)
        return {"status": "memory deleted"}
    raise HTTPException(status_code=404, detail="User memory not found.")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=9000)
