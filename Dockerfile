FROM python:3.11-slim

# התקנת Node.js
RUN apt-get update && apt-get install -y nodejs npm

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]