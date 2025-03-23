#!/bin/bash

# Installer les dépendances
pip install -r requirements.txt

# Lancer le service avec Hypercorn
hypercorn campaign_analyst:app --bind 0.0.0.0:8000
