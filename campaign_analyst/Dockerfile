FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE $PORT

CMD uvicorn campaign_analyst:asgi_app --host 0.0.0.0 --port $PORT

CMD ./start.sh
