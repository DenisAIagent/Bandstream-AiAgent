# Image de base légère
FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers nécessaires
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Commande de démarrage
CMD ["python", "campaign_analyst.py"]
