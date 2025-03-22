```bash
#!/bin/bash

# Installer asgiref sans utiliser le cache
pip install --no-cache-dir asgiref==3.8.1

# Vérifier que asgiref est bien installé
pip show asgiref

# Lancer Uvicorn
exec uvicorn campaign_supervisor.campaign_supervisor:asgi_app --host 0.0.0.0 --port $PORT
