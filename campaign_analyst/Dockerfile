# Image de base légère
FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier les dépendances
COPY requirements.txt .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code
COPY . .

# Commande de démarrage pour Railway
CMD ["hypercorn", "campaign_analyst:app", "--bind", "0.0.0.0:$PORT"]
