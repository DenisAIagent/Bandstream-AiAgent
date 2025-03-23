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

RUN touch campaign_analyst/__init__.py

EXPOSE $PORT

# Utiliser python -m hypercorn au lieu de hypercorn directement
CMD ["python", "-m", "hypercorn", "campaign_analyst.campaign_analyst:app", "--bind", "0.0.0.0:$PORT"]
