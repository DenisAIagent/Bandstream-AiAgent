#!/bin/bash

# Afficher le PATH actuel pour le débogage
echo "Current PATH: $PATH"

# Ajouter explicitement le répertoire des exécutables Python au PATH
export PATH=$PATH:/usr/local/bin

# Vérifier si hypercorn est disponible
which hypercorn || echo "hypercorn not found in PATH"

# Exécuter hypercorn via python -m pour plus de fiabilité
exec python -m hypercorn campaign_analyst.campaign_analyst:app --bind 0.0.0.0:$PORT
