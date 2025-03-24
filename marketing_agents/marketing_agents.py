from flask import Flask, request, jsonify
import openai
import os
from dotenv import load_dotenv
from cachetools import TTLCache
import logging
import json
import re

app = Flask(__name__)

# Configuration des logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Chargement des variables d'environnement
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    logger.critical("OPENAI_API_KEY manquant")
    raise ValueError("OPENAI_API_KEY manquant")

# Cache avec TTL de 24h
cache = TTLCache(maxsize=100, ttl=86400)

def clean_description(description):
    # Liste de phrases génériques à éviter
    generic_phrases = [
        r"Avec son style unique, .* rencontre un succès grandissant aux quatre coins du globe",
        r"With his unique style, .* is experiencing growing success across the globe",
        r"À chacune de ses sorties, il continue de surprendre et de créer l’engouement",
        r"With each release, .* continues to surprise his audience and build excitement",
        r"s’imposant comme une figure essentielle de la scène",
        r"cementing his place as a key figure in the .* scene"
    ]

    # Remplacer les phrases génériques par une alternative plus spécifique
    for phrase in generic_phrases:
        if re.search(phrase, description, re.IGNORECASE):
            description = re.sub(phrase, "", description, flags=re.IGNORECASE)
            description += "\nDécouvrez une expérience musicale authentique et vibrante !"
    return description.strip()

def generate_prompt(data):
    # Extraction et validation des données
    artist = data.get('artist', 'Artiste Inconnu')
    song = data.get('song', '')
    genres = data.get('genres', ['rock']) if isinstance(data.get('genres'), list) else [data.get('genres', 'rock')]
    language = data.get('language', 'français')
    tone = data.get('tone', 'authentique')
    promotion_type = data.get('promotion_type', 'sortie')
    song_link = data.get('song_link', '[insert link]')
    bio_summary = data.get('bio', f"Artiste passionné par {genres[0]} avec une approche unique.")
    bio_tone = data.get('bio_tone', 'authentique')
    bio_themes = data.get('bio_themes', 'émotion, créativité')
    target_audience = data.get('target_audience', 'tous publics')
    song_lyrics = data.get('song_lyrics', '')

    # Déterminer les artistes similaires et tendances en fonction des genres
    lookalike_artists = {
        "rock": ["Nirvana", "Pearl Jam", "Soundgarden"],
        "punk": ["Green Day", "The Offspring", "Blink-182"],
        "grunge": ["Nirvana", "Alice in Chains", "Soundgarden"],
        "pop": ["Coldplay", "Imagine Dragons", "Maroon 5"],
        "metal": ["Metallica", "Rammstein", "Nightwish"],
        "default": ["Artiste 1", "Artiste 2", "Artiste 3"]
    }
    trends = {
        "rock": ["best rock song 2025", "best playlist rock 2025", "top grunge bands 2025"],
        "punk": ["best punk song 2025", "top punk bands 2025", "punk revival 2025"],
        "grunge": ["best grunge song 2025", "grunge revival 2025", "top grunge bands 2025"],
        "pop": ["best pop song 2025", "top pop hits 2025", "pop chart toppers 2025"],
        "metal": ["best metal song 2025", "top metal bands 2025", "metal symphonique 2025"],
        "default": ["Trend 1", "Trend 2", "Trend 3"]
    }
    primary_genre = genres[0].lower()
    selected_lookalikes = lookalike_artists.get(primary_genre, lookalike_artists["default"])
    selected_trends = trends.get(primary_genre, trends["default"])

    # Prompt structuré pour GPT-4o
    prompt = f"""
    📋 OBJECTIF
    Générer un ensemble de contenus marketing pour promouvoir la {promotion_type} de l’artiste {artist}, avec un focus sur la chanson "{song}". Le contenu doit s’adapter au style musical ({', '.join(genres)}), au ton et aux thèmes de la biographie ({bio_summary}), et refléter les attentes du public cible ({target_audience}), en {language}. La réponse doit être un objet JSON structuré pour une intégration directe dans une page web, avec un respect strict des limites de caractères. Les contenus doivent être uniques, percutants, et personnalisés, en évitant les phrases génériques recyclées.

    🔄 VARIABLES PRINCIPALES
    - {{promotion_type}} : "{promotion_type}"
    - {{artist}} : "{artist}"
    - {{song}} : "{song}"
    - {{genres}} : "{', '.join(genres)}"
    - {{language}} : "{language}"
    - {{tone}} : "{tone}"
    - {{song_link}} : "{song_link}"
    - {{bio_summary}} : "{bio_summary}"
    - {{bio_tone}} : "{bio_tone}"
    - {{bio_themes}} : "{bio_themes}"
    - {{target_audience}} : "{target_audience}"
    - {{song_lyrics}} : "{song_lyrics}"

    🎸 ANALYSE CONTEXTUELLE
    1️⃣ Analyse des Genres Musicaux ({{genres}})
    - Identifier les caractéristiques et le vocabulaire spécifique :
      - Rock : énergie, riffs, puissance, authenticité
      - Punk : rébellion, énergie brute, urgence, attitude
      - Grunge : émotion brute, nostalgie, intensité, authenticité
      - Metal : intensité, riffs lourds, dramaturgie, puissance
      - Pop : mélodie, accessibilité, accrocheur, universalité, émotion
      - Électro/Dance : rythme, beats, immersion, modernité, euphorie
      - Rap/Hip-Hop : flow, authenticité, lyrics, urbanité, engagement
      - Jazz/Blues : sophistication, improvisation, émotion, profondeur, soul
      - Folk/Acoustique : simplicité, authenticité, narration, chaleur
      - Classique : élégance, virtuosité, grandeur, intemporalité
      - R&B/Soul : sensualité, groove, émotion, chaleur
      - Reggae : détente, positivisme, spiritualité, vibration
    - Si plusieurs genres, prioriser le premier comme dominant.
    - Adapter le ton recommandé par genre si {{tone}} n’est pas spécifié (ex. énergique pour rock/punk).

    2️⃣ Analyse de la Biographie ({{bio_summary}})
    - Extraire les éléments clés :
      - **Faits marquants** : Date/lieu de formation, accomplissements, collaborations.
      - **Style musical** : Influences, description du style, particularités sonores.
      - **Thèmes narratifs** : Histoires personnelles, valeurs, messages récurrents.
    - Déterminer le ton dominant ({{bio_tone}}) : Formel, Décontracté, Poétique, Engagé, Humoristique.
    - Identifier 2-3 thèmes principaux ({{bio_themes}}) : ex. rébellion, authenticité, nostalgie.

    3️⃣ Analyse des Paroles ({{song_lyrics}})
    - Identifier les thèmes principaux des paroles (ex. rébellion, défi, introspection).
    - Ne pas citer directement les paroles dans le contenu généré, mais s’en inspirer pour refléter l’ambiance et le message de la chanson.

    4️⃣ Recherche de Tendances et Artistes Similaires
    - Tendances : {json.dumps(selected_trends)}
    - Artistes similaires : {json.dumps(selected_lookalikes)}

    5️⃣ Fusion Genre-Biographie-Paroles
    - Combiner les caractéristiques du genre, les éléments biographiques, et les thèmes des paroles :
      - Prioriser {{genres}} pour le cadre général (vocabulaire, intensité).
      - Ajuster avec {{bio_tone}} pour le style d’écriture.
      - Intégrer {{bio_themes}} et les thèmes des paroles pour la cohérence thématique.
      - Si conflit entre {{tone}} et {{bio_tone}}, privilégier {{bio_tone}}.

    📱 CONTENU À GÉNÉRER
    Retourner un objet JSON avec les clés suivantes :

    1️⃣ "short_titles" : Liste de 5 titres courts (max 30 caractères)
    - Utiliser le vocabulaire spécifique à {{genres}} (ex. "riffs", "énergie brute" pour rock/punk/grunge).
    - Intégrer 1 élément thématique ({{bio_themes}}) dans au moins 2 titres.
    - Inclure {{song}} dans au moins 2 titres.
    - 2-3 appels à l’action variés adaptés au genre (ex. "Rockez", "Plongez", "Vibrez").
    - Ton aligné sur {{bio_tone}} et intensité du genre.
    - Contenu en {{language}}.
    - **Respect strict** : Aucun titre ne doit dépasser 30 caractères.
    - **Unicité** : Éviter les phrases génériques (ex. "Plongez dans l'émotion") et privilégier des formulations percutantes.

    2️⃣ "long_titles" : Liste de 5 titres longs (max 55 caractères)
    - Combiner élément accrocheur (genre), descriptif (bio), et appel à l’action.
    - Mentionner {{song}} dans 2 titres, {{artist}} dans 1-2 titres.
    - Référencer {{genres}} via vocabulaire ou ambiance (ex. "riffs percutants").
    - Intégrer un thème de {{bio_themes}} dans au moins 2 titres.
    - Adapter le ton à {{bio_tone}} avec nuances du genre.
    - Contenu en {{language}}.
    - **Respect strict** : Aucun titre ne doit dépasser 55 caractères.
    - **Unicité** : Éviter les répétitions (ex. ne pas répéter "Foo Fighters" dans tous les titres).

    3️⃣ "long_descriptions" : Liste de 5 objets avec "description" (max 80 caractères) et "character_count"
    - Structurer : accroche (genre) + contexte (bio) + appel à l’action.
    - Mentionner {{song}} in 2 descriptions, {{artist}} in 2 max.
    - Intégrer {{bio_themes}} et vocabulaire de {{genres}}.
    - Inclure 3 appels à l’action variés (ex. "Plongez", "Vibrez", "Découvrez").
    - Aligner le style sur {{bio_tone}} et l’intensité du genre.
    - Contenu en {{language}}.
    - **Respect strict** : Aucune description ne doit dépasser 80 caractères.
    - **Unicité** : Éviter les phrases génériques (ex. "Plongez dans l'énergie") et varier les formulations.

    4️⃣ "youtube_description_short" : Objet avec "description" (max 120 caractères) et "character_count"
    - Créer une description concise pour YouTube, adaptée à {{genres}} et {{bio_tone}}.
    - Mentionner {{song}} et inclure un appel à l’action.
    - Inclure des mots-clés pour le SEO (ex. {{artist}}, {{song}}, {{genres}}).
    - **Respect strict** : Ne pas dépasser 120 caractères.
    - **Unicité** : Éviter les phrases génériques (ex. "Plongez dans le clip rock") et privilégier une formulation percutante.

    5️⃣ "youtube_description_full" : Objet avec "description" (max 5000 caractères) et "character_count"
    - Structurer :
      - **Introduction** (1-2 phrases) : Une accroche captivante mentionnant {{artist}}, {{song}}, et un élément clé de {{bio_summary}} (ex. une anecdote ou un fait marquant).
      - **Corps** : 
        - Contexte biographique ({{bio_summary}}). Inclure un fait marquant ou une anecdote tirée de la biographie pour renforcer l’authenticité (ex. une référence à une performance live, un moment clé de la carrière, ou une influence majeure).
        - Description de la sortie ({{song}}, {{promotion_type}}, lien avec {{genres}} et {{bio_themes}}). S’inspirer des thèmes des paroles ({{song_lyrics}}) pour refléter l’ambiance et le message de la chanson, sans citer directement les paroles.
        - Inclure un extrait des paroles (1-2 lignes significatives) pour donner un aperçu, mais ne pas inclure l’intégralité des paroles.
        - Intégrer une référence aux tendances ({json.dumps(selected_trends)}) et aux artistes similaires ({json.dumps(selected_lookalikes)}) pour contextualiser et optimiser le SEO.
      - **Conclusion** : Invitation à écouter avec un appel à l’action (ex. "Regardez maintenant sur {{song_link}} ! Likez, commentez et abonnez-vous pour ne rien manquer !").
    - **Mise en Page** :
      - Utiliser des sauts de ligne (\n) pour aérer le texte.
      - Séparer les sections avec des emojis (ex. 🔔 pour les abonnements, 📌 pour les crédits).
      - Inclure des placeholders pour les liens (ex. "collez votre smartlink", "collez le lien de votre chaîne YouTube").
      - Ajouter des liens sociaux (Instagram, TikTok, site web) avec des placeholders.
      - Ajouter 3-5 hashtags pertinents à la fin (ex. #{artist}, #{song}, #{genres}).
    - Intégrer {{bio_themes}}, {{genres}}, et un ton aligné sur {{bio_tone}}.
    - **Respect strict** : Ne pas dépasser 5000 caractères.
    - **SEO** :
      - Inclure {{artist}}, {{song}}, et {{genres}} dans les premières lignes.
      - Intégrer les tendances ({json.dumps(selected_trends)}) pour capter les recherches spécifiques.
      - Mentionner les artistes similaires ({json.dumps(selected_lookalikes)}) pour apparaître dans les recherches associées.
      - Encourager l’engagement (ex. "Abonnez-vous", "Likez", "Commentez").
    - **Unicité** : Éviter les phrases génériques recyclées comme "Avec son style unique, [artiste] rencontre un succès grandissant..." ou "À chacune de ses sorties, il continue de surprendre...". Créer une description qui reflète l’identité unique de l’artiste et de la chanson.
    - **Exemple de description attendue** :
      - Pour Foo Fighters : "{artist} - {song} : un clip qui défie les conventions !\n\nNés à Seattle en 1994 des cendres de Nirvana, {artist}, menés par Dave Grohl, reviennent avec {song}, un clip qui capture l’essence rebelle du grunge et l’énergie brute du punk. Ce titre, enregistré dans des conditions live pour garder leur authenticité, est un cri de défi contre la conformité, un thème cher au groupe depuis leurs débuts dans les clubs underground. Écoutez un extrait : 'What if I say I will never surrender?' Ce morceau est déjà nommé parmi les 'best rock songs 2025', aux côtés de légendes comme {selected_lookalikes[0]} et {selected_lookalikes[1]}.\n\n🔔 Abonnez-vous pour ne rien manquer ! 👉 collez le lien de votre chaîne YouTube\n\n📌 Crédits :\nMontage : collez le nom du monteur\nVidéos : collez le nom du vidéaste\n\nLabel : collez l'email du label\nBooking Europe, Africa & North America : collez l'email de booking (Europe, Afrique, Amérique du Nord)\nBooking Latin America : collez l'email de booking (Amérique Latine)\n\nSuivez {artist} sur :\nInstagram : collez votre handle Instagram\nTikTok : collez votre handle TikTok\nWebsite : collez l'URL de votre site web\n\n#{artist} #{song} #rock #punkrock #grunge"

    6️⃣ "analysis" : Objet avec :
      - "trends" : Liste de 3 mots-clés "long tail" liés à {{genres}} et 2025 (ex. ["best rock song 2025", "best playlist rock 2025", "top grunge bands 2025"]).
      - "lookalike_artists" : Liste de 3 artistes similaires mais distincts, identifiés via la recherche simulée (ex. ["Nirvana", "Pearl Jam", "Soundgarden"]).
      - "artist_image_url" : URL fictive (ex. "https://example.com/{artist.lower().replace(' ', '-')}.jpg").

    **Format de sortie** :
    {{
      "short_titles": ["titre1", "titre2", "titre3", "titre4", "titre5"],
      "long_titles": ["titre1", "titre2", "titre3", "titre4", "titre5"],
      "long_descriptions": [
        {{"description": "desc1", "character_count": 37}},
        {{"description": "desc2", "character_count": 41}},
        {{"description": "desc3", "character_count": 38}},
        {{"description": "desc4", "character_count": 34}},
        {{"description": "desc5", "character_count": 41}}
      ],
      "youtube_description_short": {{"description": "desc", "character_count": 41}},
      "youtube_description_full": {{"description": "desc", "character_count": 200}},
      "analysis": {{
        "trends": {json.dumps(selected_trends)},
        "lookalike_artists": {json.dumps(selected_lookalikes)},
        "artist_image_url": "https://example.com/{artist.lower().replace(' ', '-')}.jpg"
      }}
    }}
    """
    return prompt

@app.route('/generate_ads', methods=['POST'])
def generate_ads():
    try:
        data = request.get_json()
        if not data:
            logger.error("Aucune donnée JSON fournie")
            return jsonify({"error": "Aucune donnée fournie"}), 400

        # Vérification des champs obligatoires
        required_fields = ['artist', 'genres', 'language', 'promotion_type']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            logger.error(f"Champs manquants : {missing_fields}")
            return jsonify({"error": f"Champs manquants : {missing_fields}"}), 400

        # Ajouter les paroles de la chanson si elles ne sont pas fournies
        if 'song_lyrics' not in data:
            data['song_lyrics'] = ""

        # Clé de cache
        cache_key = "_".join([str(data.get(field, '')) for field in required_fields + ['song', 'tone']])
        logger.info(f"Clé de cache : {cache_key}")

        # Vérification du cache
        if cache_key in cache:
            logger.info(f"Réponse trouvée dans le cache pour : {cache_key}")
            cached_result = cache[cache_key]
            if not cached_result or "short_titles" not in cached_result:
                logger.warning(f"Données en cache vides ou corrompues pour : {cache_key}")
                cache.pop(cache_key)
            else:
                return jsonify(cached_result)

        # Génération du prompt
        prompt = generate_prompt(data)
        logger.info("Prompt généré avec succès")

        # Appel à l'API OpenAI avec GPT-4o
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.7
        )
        result = response.choices[0].message['content']
        logger.info("Réponse OpenAI reçue")

        # Nettoyer la réponse pour enlever les balises ```json ... ```
        result_cleaned = re.sub(r'^```json\n|\n```$', '', result).strip()

        # Vérification que la réponse est un JSON valide
        try:
            result_json = json.loads(result_cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Réponse OpenAI non-JSON après nettoyage : {result_cleaned}")
            return jsonify({"error": "La génération a échoué : réponse non-JSON"}), 500

        # Vérification des clés attendues
        required_keys = ["short_titles", "long_titles", "long_descriptions", "youtube_description_short", "youtube_description_full", "analysis"]
        missing_keys = [key for key in required_keys if key not in result_json]
        if missing_keys:
            logger.error(f"Clés manquantes dans la réponse JSON : {missing_keys}")
            return jsonify({"error": f"Clés manquantes dans la réponse : {missing_keys}"}), 500

        # Vérification du nombre d'éléments
        if len(result_json["short_titles"]) != 5:
            logger.error(f"Nombre incorrect de short_titles : {len(result_json['short_titles'])}")
            return jsonify({"error": "Nombre incorrect de short_titles"}), 500
        if len(result_json["long_titles"]) != 5:
            logger.error(f"Nombre incorrect de long_titles : {len(result_json['long_titles'])}")
            return jsonify({"error": "Nombre incorrect de long_titles"}), 500
        if len(result_json["long_descriptions"]) != 5:
            logger.error(f"Nombre incorrect de long_descriptions : {len(result_json['long_descriptions'])}")
            return jsonify({"error": "Nombre incorrect de long_descriptions"}), 500

        # Nettoyer la description YouTube pour éviter les phrases génériques
        result_json["youtube_description_full"]["description"] = clean_description(result_json["youtube_description_full"]["description"])
        result_json["youtube_description_full"]["character_count"] = len(result_json["youtube_description_full"]["description"])

        # Mise en cache et réponse
        cache[cache_key] = result_json
        logger.info(f"Contenu généré et mis en cache pour : {cache_key}")
        return jsonify(result_json)

    except openai.error.OpenAIError as e:
        logger.error(f"Erreur OpenAI : {str(e)}")
        return jsonify({"error": f"Erreur OpenAI : {str(e)}"}), 500
    except Exception as e:
        logger.error(f"Erreur inattendue : {str(e)}")
        return jsonify({"error": f"Erreur interne : {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
