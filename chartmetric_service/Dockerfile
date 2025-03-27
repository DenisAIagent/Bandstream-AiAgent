FROM python:3.10-slim

WORKDIR /app

# Copier requirements.txt en premier pour exploiter le cache des couches Docker
COPY requirements.txt .

# Installer les dépendances avec --no-cache-dir pour éviter les problèmes de cache
RUN pip install --no-cache-dir -r requirements.txt

# Vérifier que hypercorn est bien installé
RUN which hypercorn || echo "ERREUR: hypercorn n'est pas installé!"

# Copier le reste du code
COPY . .

# Définir la commande de démarrage
CMD hypercorn app:app --bind 0.0.0.0:$PORT
