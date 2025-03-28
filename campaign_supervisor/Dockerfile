FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier tout le contenu du répertoire courant dans /app
COPY . .

# Commande pour démarrer l'application
CMD ["uvicorn", "campaign_supervisor:asgi_app", "--host", "0.0.0.0", "--port", "8080"]
