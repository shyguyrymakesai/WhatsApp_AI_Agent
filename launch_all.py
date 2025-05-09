import subprocess
import time
import os


# Helper to launch a process in a new console window
def launch(command, cwd=None):
    return subprocess.Popen(
        command,
        cwd=cwd,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )


# ---------------------- Launch WhatsApp API (Node.js) ----------------------
whatsapp_api = launch(["node", "index.js"], cwd="whatsapp-bot")

# ---------------------- Launch MCP Server (FastAPI) ----------------------
# Ensure the working directory is project root so imports resolve correctly
mcp_server = launch(
    [
        "uvicorn",
        "src.memory.mcp_server:app",  # module path
        "--host",
        "0.0.0.0",
        "--port",
        "9000",
    ],
    cwd=os.getcwd(),  # project root
)

# ---------------------- Launch Duckling Server (Docker) ----------------------
duckling = launch(["docker", "run", "--rm", "-p", "8000:8000", "rasa/duckling"])

# ---------------------- Launch FastAPI Agent Receiver ----------------------
# give everything a moment to start
print("⏳ Waiting for services to spin up...")
time.sleep(5)

# Set environment variable for receiver port
os.environ.setdefault("FASTAPI_PORT", "8001")

receiver = launch(
    [
        "uvicorn",
        "src.receiver:app",
        "--host",
        "0.0.0.0",
        "--port",
        os.environ["FASTAPI_PORT"],
        "--reload",
    ],
    cwd=os.getcwd(),
)

# ---------------------- Keep Launcher Alive ----------------------
print("✅ All services launched! Press Ctrl+C to exit…")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n👋 Shutting down services…")
    for proc in (whatsapp_api, mcp_server, duckling, receiver):
        proc.terminate()
