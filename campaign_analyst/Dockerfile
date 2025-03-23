FROM python:3.9

WORKDIR /app

# Copier le requirements.txt à la racine du dépôt
COPY analyst-requirements.txt .

# Installer les dépendances sans utiliser le cache
RUN pip install --no-cache-dir -r analyst-requirements.txt

# Copier le reste des fichiers de l'application
COPY . .

RUN touch campaign_analyst/__init__.py

EXPOSE $PORT

# Utiliser une commande simple pour tester
CMD ["echo", "Hello, Railway!"]
