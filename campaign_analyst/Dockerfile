FROM python:3.9-slim

WORKDIR /app

COPY campaign_analyst/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN touch campaign_analyst/__init__.py

EXPOSE $PORT

CMD ["hypercorn", "campaign_analyst.campaign_analyst:app", "--bind", "0.0.0.0:$PORT"]
