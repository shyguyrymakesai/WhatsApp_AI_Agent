"""LangChain tool that returns the current timestamp."""

from datetime import datetime

from langchain.tools import Tool


def get_time() -> str:
    """Return the current time in ISO-8601 format."""

    return f"The current time is {datetime.now().isoformat(timespec='seconds')}"


GetTime = Tool.from_function(
    name="GetTime",
    func=get_time,
    description="Provides the current datetime.",
)
