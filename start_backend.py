import sys
import os
import subprocess
import multiprocessing
import time

# --- Setup Python path to include /src ---
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))


# --- Auto-install missing packages from requirements.txt ---
def install_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if os.path.exists(requirements_path):
        print("📚 Installing dependencies from requirements.txt...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-r", requirements_path]
            )
            print("✅ All dependencies installed.")
        except subprocess.CalledProcessError:
            print(
                "❌ Failed to install requirements. Please check your internet connection and try again."
            )
            sys.exit(1)
    else:
        print("⚠️ requirements.txt not found. Skipping dependency installation.")


install_requirements()


# --- Functions to start services ---
def start_receiver():
    import uvicorn

    uvicorn.run("receiver:app", host="0.0.0.0", port=8000, reload=True)


def start_reminder_scheduler():
    from src.reminder_scheduler import run_scheduler

    run_scheduler()


# --- Main orchestrator ---
if __name__ == "__main__":
    print("🚀 Starting backend services...")

    receiver_process = multiprocessing.Process(target=start_receiver)
    reminder_process = multiprocessing.Process(target=start_reminder_scheduler)

    receiver_process.start()
    time.sleep(2)  # Give receiver time to start
    reminder_process.start()

    receiver_process.join()
    reminder_process.join()
