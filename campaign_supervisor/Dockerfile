FROM python:3.9-slim

WORKDIR /app

# Copier les fichiers de dépendances
COPY requirements.txt .

# Installer les dépendances sans utiliser le cache
RUN pip install --no-cache-dir -r requirements.txt

# Vérifier explicitement que asgiref est installé
RUN pip install --no-cache-dir asgiref==3.8.1

# Copier le reste des fichiers de l'application
COPY . .

# Exposer le port dynamiquement via la variable $PORT
EXPOSE $PORT

# Commande de démarrage avec Uvicorn (serveur ASGI)
CMD uvicorn campaign_supervisor.campaign_supervisor:asgi_app --host 0.0.0.0 --port $PORT
