FROM python:3.11-slim

WORKDIR /app

# install your Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy everything else
COPY . .

# start the FastAPI server
CMD ["uvicorn", "src.receiver:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
