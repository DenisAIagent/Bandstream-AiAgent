FROM python:3.9-slim

WORKDIR /app

# Installer les dépendances sans utiliser le cache
pip install --no-cache-dir -r analyst-requirements.txt

# Copier le reste des fichiers de l'application
COPY . .

# Exposer le port dynamiquement via la variable $PORT
EXPOSE $PORT

# Commande de démarrage avec Uvicorn (serveur ASGI)
CMD ["uvicorn", "campaign_supervisor.campaign_supervisor:asgi_app", "--host", "0.0.0.0", "--port", "$PORT"]
