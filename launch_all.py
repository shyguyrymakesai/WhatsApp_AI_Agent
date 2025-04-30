import subprocess
import time
import os

# ---------------------- Launch WhatsApp API (Node.js) ----------------------
whatsapp_api = subprocess.Popen(
    ["node", "index.js"],
    cwd="whatsapp-bot",  # Make sure this is the correct folder
    creationflags=subprocess.CREATE_NEW_CONSOLE,
)

# ---------------------- Launch MCP Server ----------------------
mcp_server = subprocess.Popen(
    ["uvicorn", "memory.mcp_server:app", "--host", "0.0.0.0", "--port", "9000"],
    creationflags=subprocess.CREATE_NEW_CONSOLE,
)

# ---------------------- Launch FastAPI Agent Receiver ----------------------
# Set environment variable for receiver
os.environ["FASTAPI_PORT"] = "8001"

# Wait a little so WhatsApp and MCP have time to start
time.sleep(2)

# Pull port from environment
fastapi_port = os.environ["FASTAPI_PORT"]

receiver = subprocess.Popen(
    [
        "uvicorn",
        "src.receiver:app",
        "--host",
        "0.0.0.0",
        "--port",
        fastapi_port,
        "--reload",
    ],
    creationflags=subprocess.CREATE_NEW_CONSOLE,
)

# ---------------------- Keep Launcher Alive ----------------------
print("✅ All services launched! Waiting to keep console open...")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n👋 Exiting...")
