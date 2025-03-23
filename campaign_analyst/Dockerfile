# Image de base
FROM python:3.11-slim

# Répertoire de travail
WORKDIR /app

# Copie des dépendances
COPY requirements.txt .

# Installation des dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY . .

# Commande de démarrage compatible avec Railway
CMD ["hypercorn", "campaign_analyst:app", "--bind", "0.0.0.0:$PORT"]
