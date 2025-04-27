# receiver.py

from fastapi import FastAPI, Request
import uvicorn

from agent.agent import Agent
from tools.whatsapp_snd_tool import SendWhatsappMsg
from tools.whatsapp_rcv_tool import receive_whatsapp_message

# Initialize app
app = FastAPI()

# Initialize agent
agent = Agent(tools=[SendWhatsappMsg])


@app.post("/incoming")
async def incoming_whatsapp_message(request: Request):
    """
    Endpoint to receive incoming WhatsApp messages forwarded by Node server.
    """
    payload = await request.json()
    print("📩 Incoming payload:", payload)

    extracted = receive_whatsapp_message(payload)

    if "error" in extracted:
        return {"status": "error", "details": extracted["error"]}

    user_message = extracted["user_message"]
    user_number = extracted["user_number"]

    # Let agent think and act
    tool_name, tool_args = agent.think_llm(user_message)

    # Update number dynamically based on incoming sender
    if tool_args and "number" in tool_args:
        tool_args["number"] = user_number

    agent.act(tool_name, tool_args)

    return {"status": "success"}


# Run the FastAPI server
if __name__ == "__main__":
    uvicorn.run("receiver:app", host="0.0.0.0", port=8000, reload=True)
