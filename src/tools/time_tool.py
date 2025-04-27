import requests
from pydantic import BaseModel
from langchain.tools import Tool

def get_time():
    from datetime import datetime
    return f"The current time is {datetime.now()}"

GetTime = Tool.from_function(
    name = "GetTime",
    func = get_time, 
    description = "Provides the current datetime."
)