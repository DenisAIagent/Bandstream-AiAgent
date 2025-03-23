FROM python:3.9

WORKDIR /app

# Mettre à jour pip pour éviter les problèmes d’installation
RUN pip install --upgrade pip

# Copier le requirements.txt à la racine du dépôt
COPY analyst-requirements.txt .

# Installer les dépendances sans utiliser le cache
RUN pip install --no-cache-dir -r analyst-requirements.txt

# Vérifier que hypercorn est bien installé en utilisant python -m
RUN python -m hypercorn --version

# Copier le reste des fichiers de l'application
COPY . .

# Rendre le script start.sh exécutable
RUN chmod +x start.sh

RUN touch campaign_analyst/__init__.py

EXPOSE $PORT

# Utiliser le script start.sh comme point d'entrée
CMD ["./start.sh"]
