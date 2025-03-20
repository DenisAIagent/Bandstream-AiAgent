# Band Stream Crew IA Agent - Marketing Agent

Ce module fait partie du projet Band Stream Crew IA Agent, une application modulaire pour générer des campagnes marketing pour des artistes musicaux.

## Description

Le Marketing Agent est responsable de la génération de contenu publicitaire pour les artistes musicaux. Il utilise l'API OpenAI pour créer des titres courts, des titres longs et des descriptions détaillées qui peuvent être utilisés dans des campagnes Google Ads.

## Fonctionnalités

- Génération de 5 titres courts accrocheurs (maximum 30 caractères)
- Génération de 5 titres longs plus descriptifs (maximum 90 caractères)
- Génération de 5 descriptions longues détaillées (environ 150-200 mots chacune)
- Affichage des résultats dans un template HTML élégant et responsive
- API REST pour l'intégration avec d'autres modules du projet

## Installation

1. Décompressez le fichier `band_stream_marketing_agent.zip`
2. Installez les dépendances :

```bash
pip install -r requirements.txt
```

3. Configurez votre clé API OpenAI dans le fichier `.env` :

```
OPENAI_API_KEY=votre_clé_api_openai
```

## Utilisation

### Démarrer le serveur

```bash
python marketing_agent.py
```

Le serveur démarre sur le port 5000 par défaut.

### Prévisualisation avec des données d'exemple

Accédez à `http://localhost:5000/preview` pour voir un exemple de résultat avec des données prédéfinies.

### Générer du contenu via l'API

Envoyez une requête POST à `http://localhost:5000/generate` avec un payload JSON comme celui-ci :

```json
{
    "artist_name": "Nom de l'artiste",
    "single_name": "Nom du single",
    "similar_artists": ["Artiste similaire 1", "Artiste similaire 2", "Artiste similaire 3"],
    "genre": "Genre musical",
    "mood": "Ambiance"
}
```

La réponse contiendra à la fois le HTML généré et les données structurées :

```json
{
    "html": "...",
    "data": {
        "artist_name": "Nom de l'artiste",
        "single_name": "Nom du single",
        "similar_artists": ["..."],
        "short_titles": ["..."],
        "long_titles": ["..."],
        "long_descriptions": ["..."],
        "artist_image_url": null
    }
}
```

## Intégration avec Band Stream Crew IA Agent

Ce module est conçu pour s'intégrer avec les autres agents du projet Band Stream Crew IA Agent :

1. **MAIN** (interface utilisateur) peut appeler l'API `/generate` pour obtenir du contenu publicitaire
2. **SUPERVISOR** (chef de projet) peut orchestrer les appels entre l'ANALYST et le MARKETING agent
3. **ANALYST** (recherche d'insights) peut fournir les données d'entrée (artistes similaires, etc.)
4. **OPTIMIZER** (optimisation) peut utiliser les résultats pour optimiser les campagnes

## Personnalisation

Le template HTML (`template.html`) peut être modifié pour correspondre à votre charte graphique. Il utilise le moteur de template Jinja2 avec les variables suivantes :

- `{{ artist_name }}` - Nom de l'artiste
- `{{ single_name }}` - Nom du single
- `{{ similar_artists }}` - Liste des artistes similaires
- `{{ short_titles }}` - Liste des titres courts
- `{{ long_titles }}` - Liste des titres longs
- `{{ long_descriptions }}` - Liste des descriptions longues
- `{{ artist_image_url }}` - URL de l'image de l'artiste (si disponible)

## Notes techniques

- Le serveur Flask est configuré pour le développement. Pour la production, utilisez un serveur WSGI comme Gunicorn.
- La fonction `get_artist_image_url()` est un placeholder. Dans une implémentation réelle, vous pourriez utiliser l'API Spotify ou une autre source pour obtenir des images d'artistes.
- Si la clé API OpenAI n'est pas configurée ou si une erreur se produit, le système utilisera des réponses par défaut.
