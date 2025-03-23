FROM python:3.9-slim

WORKDIR /app

# Copier le requirements.txt spécifique à campaign_analyst
COPY campaign_analyst/requirements.txt .

# Installer les dépendances sans utiliser le cache
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste des fichiers de l'application
COPY . .

RUN touch campaign_analyst/__init__.py

EXPOSE $PORT

CMD ["hypercorn", "campaign_analyst:app", "--bind", "0.0.0.0:$PORT"]
