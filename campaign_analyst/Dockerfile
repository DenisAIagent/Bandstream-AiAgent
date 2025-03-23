FROM python:3.9-slim

# Installer les dépendances système nécessaires pour compiler certains packages
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Créer et activer un environnement virtuel
RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Mettre à jour pip pour éviter les problèmes d’installation
RUN pip install --upgrade pip

# Copier le requirements.txt spécifique à campaign_analyst
COPY campaign_analyst/requirements.txt .

# Installer les dépendances sans utiliser le cache
RUN pip install --no-cache-dir -r requirements.txt

# Vérifier que hypercorn est bien installé
RUN hypercorn --version

# Vérifier le chemin de l’exécutable hypercorn
RUN which hypercorn

# Copier le reste des fichiers de l'application
COPY . .

RUN touch campaign_analyst/__init__.py

EXPOSE $PORT

CMD ["hypercorn", "campaign_analyst.campaign_analyst:app", "--bind", "0.0.0.0:$PORT"]
