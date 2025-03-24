from flask import Flask, request
import openai
import os
from dotenv import load_dotenv
from cachetools import TTLCache
import json
import logging

# Initialisation de l'application Flask
app = Flask(__name__)

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration des clés API (via variables d'environnement)
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Cache pour les résultats (24h)
cache = TTLCache(maxsize=100, ttl=86400)

@app.route('/generate_ads', methods=['POST'])
def generate_ads():
    # Récupérer les données de la requête
    data = request.get_json()
    artist = data.get('artist')
    genres = data.get('genres')
    language = data.get('language')
    tone = data.get('tone')
    promotion_type = data.get('promotion_type')
    song = data.get('song', '')  # Ajout du champ song
    song_link = data.get('song_link', '[insert link]')  # Récupérer le lien de la chanson
    artist_bio = data.get('artist_bio', f"Formé en 2013 en Suisse, {artist} est connu pour son approche théâtrale et cinématographique, mêlant metal gothique et éléments industriels, créant un univers sombre et dramatique.")

    if not artist or not genres or not language or not tone or not promotion_type:
        logger.error("Missing required fields in request")
        return {"error": "Missing required fields"}, 400

    # Clé pour le cache
    cache_key = f"{artist}_{genres[0]}_{language}_{tone}_{promotion_type}_{song}"
    logger.info(f"Generated cache key: {cache_key}")

    # Vérifier si le résultat est en cache
    if cache_key in cache:
        logger.info(f"Using cached OpenAI response for key: {cache_key}")
        return cache[cache_key]

    # Générer le prompt avec la partie optimisée
    prompt = f"""
    📋 OBJECTIF
    Générer un ensemble complet de contenus marketing percutants pour promouvoir la {promotion_type} d’un artiste musical, avec un focus sur une chanson spécifique. Le contenu s’adaptera automatiquement au style musical sélectionné ({genres}) et au ton de la biographie de l’artiste ({artist_bio}), tout en étant optimisé pour maximiser l’engagement sur différentes plateformes.

    🔄 VARIABLES ESSENTIELLES
    - {{promotion_type}}: Type de promotion musicale → "{promotion_type}"
    - {{artist}}: Nom de l’artiste ou du groupe → "{artist}"
    - {{song}}: Titre de la chanson à promouvoir → "{song}"
    - {{genres}}: Styles musicaux (séparés par virgules) → "{genres}"
    - {{language}}: Langue du contenu généré → "{language}"
    - {{tone}}: Ton et attitude du contenu → "{tone}"
    - {{song_link}}: Lien vers la chanson/clip → "{song_link}"
    - {{artist_bio}}: Biographie complète de l’artiste → "{artist_bio}"

    🎸 ANALYSE CONTEXTUELLE
    Avant de générer le contenu, analyser la biographie de l’artiste ({artist_bio}) et le genre musical ({genres}) pour extraire :
    - **Ton dominant de la biographie** : Dramatique, mystique (style sombre et théâtral, avec une écriture évocatrice).
    - **Thèmes récurrents dans la biographie** : Théâtralité, mysticisme, tension dramatique, univers cinématographique.
    - **Éléments distinctifs de l’artiste** : Approche théâtrale et cinématographique, mélange de metal gothique et indus, création d’un univers sombre et dramatique.
    - **Caractéristiques du genre musical** :
      - **Rock théâtral** : Dramaturgie, mise en scène musicale, émotions exacerbées.
      - **Metal gothique** : Ambiance sombre, riffs lourds, esthétique mystique.
      - **Indus** : Sonorités industrielles, textures mécaniques, intensité dramatique.
    Tout le contenu généré doit respecter l’identité artistique extraite de la biographie et être exclusivement dans la langue {language} spécifiée.

    📱 CONTENU À GÉNÉRER

    1️⃣ TITRES COURTS (5 titres, max 30 caractères chacun)
    **Objectif** : Capter l’attention immédiatement avec un impact maximal.
    **Structure recommandée** :
    - Verbe d’action puissant + élément accrocheur.
    - Terme émotionnel fort + référence musicale.
    - Référence au style {genres} avec terminologie adaptée.
    **Adaptation au genre musical** :
    - **Rock théâtral** : Utiliser un vocabulaire dramatique et évocateur (ex : "Plongez dans l’ombre", "Vibrez dans le mystère").
    - **Metal gothique** : Mettre en avant l’esthétique sombre et mystique (ex : "Mysticisme gothique", "Riffs sombres").
    - **Indus** : Souligner l’intensité et les textures mécaniques (ex : "Son indus percutant", "Tension mécanique").
    **Intégration biographique** :
    - Incorporer un élément distinctif : Approche théâtrale et cinématographique.
    - Adapter le ton : Dramatique, mystique.
    - Refléter les thèmes : Mysticisme, tension dramatique.
    **Exigences précises** :
    - 2-3 titres avec appels à l’action directs adaptés au genre (ex : "Écoutez maintenant", "Plongez dans l’ombre").
    - 2-3 titres évoquant l’ambiance ou l’émotion de la chanson (ex : "Mysticisme gothique", "Tension dramatique").
    - Mention de {song} dans au moins 2 titres.
    - Maximum 1 titre mentionnant {artist}.
    - Ton correspondant à la fusion entre {genres} et le ton de la biographie.
    - Contenu exclusivement en {language}.
    **Exemples adaptés** :
    - "Salve Regina : mystère gothique ! (30 / 30)"
    - "Plongez dans l’ombre ! (22 / 30)"
    - "Salve Regina : vibrez ! (22 / 30)"
    - "Tension indus, écoutez ! (24 / 30)"
    - "Théâtre sombre, découvrez ! (27 / 30)"

    2️⃣ TITRES LONGS (5 titres, max 55 caractères chacun)
    **Objectif** : Développer l’accroche avec plus de contexte et de détails.
    **Structure recommandée** :
    - Élément accrocheur + élément descriptif + élément incitatif.
    - Référence musicale + évocation émotionnelle + appel à l’action.
    **Adaptation au genre musical** :
    - **Rock théâtral** : Développer sur la dramaturgie et l’émotion (ex : "Un voyage théâtral dans l’ombre").
    - **Metal gothique** : Mettre en avant l’esthétique sombre et mystique (ex : "Un hymne gothique empreint de mystère").
    - **Indus** : Souligner l’intensité et les textures industrielles (ex : "Une tension indus qui vous happe").
    **Intégration biographique** :
    - Incorporer un élément narratif : Approche théâtrale et cinématographique.
    - Faire référence à l’évolution artistique : Création d’un univers sombre et dramatique.
    - Refléter l’approche créative : Mélange de metal gothique et indus.
    **Exigences précises** :
    - 2-3 titres incluant un appel à l’action explicite adapté au genre (ex : "Découvrez le mystère", "Vibrez dans l’ombre").
    - 2-3 titres évoquant l’expérience d’écoute ou l’impact émotionnel.
    - Mention de {song} dans au moins 2 titres.
    - Référence à {artist} dans 1-2 titres maximum.
    - Inclusion d’au moins un élément spécifique au style {genres} dans chaque titre.
    - Ton correspondant à la fusion entre {genres} et le ton de la biographie.
    - Contenu exclusivement en {language}.
    **Exemples adaptés** :
    - "Salve Regina : un voyage gothique ! (34 / 55)"
    - "Plongez dans un univers théâtral ! (34 / 55)"
    - "Salve Regina : mystère indus ! (29 / 55)"
    - "Vibrez avec un son dramatique ! (30 / 55)"
    - "Silver Dust : tension gothique ! (31 / 55)"

    3️⃣ DESCRIPTIONS LONGUES (5 descriptions, max 80 caractères chacune)
    **Objectif** : Approfondir l’intérêt et créer une connexion émotionnelle.
    **Structure recommandée** :
    - Accroche émotionnelle + élément descriptif + appel à l’action clair.
    - Référence thématique + élément musical distinctif + incitation.
    **Adaptation au genre musical** :
    - **Rock théâtral** : Mettre en avant la dramaturgie et l’émotion (ex : "Un voyage théâtral dans l’ombre").
    - **Metal gothique** : Évoquer l’ambiance sombre et mystique (ex : "Un hymne gothique empreint de mystère").
    - **Indus** : Souligner l’intensité et les textures industrielles (ex : "Une tension indus qui vous happe").
    **Intégration biographique** :
    - Incorporer des thèmes : Mysticisme, tension dramatique.
    - Faire référence à l’approche créative : Mélange de metal gothique et indus.
    - Adapter le style d’écriture : Dramatique, mystique.
    **Exigences précises** :
    - Chaque description doit contenir au moins un appel à l’action.
    - Au moins 3 descriptions avec des appels à l’action variés adaptés au genre (ex : "Écoutez maintenant", "Regardez le clip", "Plongez dans l’ombre").
    - Mention de {song} dans au moins 2 descriptions.
    - Référence à {artist} dans 2 descriptions maximum.
    - Évocation des thèmes : Mysticisme, rédemption, tension dramatique.
    - Utilisation de termes évocateurs liés aux genres {genres}.
    - Ton correspondant à la fusion entre {genres} et le ton de la biographie.
    - Contenu exclusivement en {language}.
    **Exemples adaptés** :
    - "Salve Regina : mystère gothique et riffs ! Écoutez ! (49 / 80)"
    - "Un voyage théâtral dans l’ombre ! Plongez dedans ! (48 / 80)"
    - "Salve Regina : tension indus et mysticisme ! Regardez ! (52 / 80)"
    - "Silver Dust : un hymne dramatique ! Écoutez maintenant ! (53 / 80)"
    - "Ambiance sombre et industrielle ! Vibrez avec nous ! (49 / 80)"

    4️⃣ DESCRIPTION YOUTUBE
    **A. Description Courte (max 120 caractères)** :
    **Objectif** : Capturer l’attention immédiatement dans les aperçus et notifications.
    **Structure recommandée** :
    - Accroche puissante + référence au style + appel à l’action fort.
    **Adaptation au genre et à la biographie** :
    - Adapter le vocabulaire : Dramaturgie, mysticisme, intensité.
    - Intégrer un élément distinctif : Approche théâtrale et cinématographique.
    - Ajuster le ton : Dramatique, mystique.
    **Exigences précises** :
    - Inclusion obligatoire de {song}.
    - Mention de {artist} recommandée.
    - Référence au style {genres} ou à l’ambiance.
    - Appel à l’action clair et incitatif adapté au genre.
    - Langage reflétant la fusion entre {genres} et le ton de la biographie.
    - Contenu exclusivement en {language}.
    **Exemple adapté** :
    - "Plongez dans le mystère de Salve Regina par Silver Dust ! Écoutez ! (65 / 120)"

    **B. Description Complète (max 5000 caractères)** :
    **Objectif** : Fournir une présentation complète et engageante pour maximiser la conversion.
    **Structure recommandée** :
    - [INTRODUCTION CAPTIVANTE - 10-15%] : Présentation percutante de {artist} et {song}, référence à un élément marquant de la biographie.
    - [DESCRIPTION IMMERSIVE DE LA CHANSON - 30-40%] : Analyse évocatrice de {song}, description de l’impact émotionnel, références aux éléments musicaux distinctifs.
    - [CONTEXTE ARTISTIQUE - 20-25%] : Positionnement dans le parcours de l’artiste, référence à l’évolution stylistique.
    - [APPELS À L’ACTION STRATÉGIQUES - 15-20%] : Écouter la chanson, s’abonner, suivre sur les réseaux sociaux.
    - [SECTION TECHNIQUE ET CRÉDITS - 5-10%] : Informations sur la production, crédits.
    - [HASHTAGS OPTIMISÉS] : Hashtags liés au style musical.
    **Adaptation au genre musical** :
    - **Rock théâtral** : Mettre en avant la dramaturgie et l’émotion.
    - **Metal gothique** : Évoquer l’ambiance sombre et mystique.
    - **Indus** : Souligner l’intensité et les textures industrielles.
    **Intégration biographique** :
    - Introduction : Mentionner l’approche théâtrale et cinématographique.
    - Description : Relier la sortie aux thèmes de mysticisme et tension.
    - Contexte : Situer la sortie dans l’évolution artistique de Silver Dust.
    - Style d’écriture : Dramatique, mystique.
    **Exigences générales** :
    - Paragraphes structurés avec progression logique.
    - Variation des longueurs de phrases pour un rythme dynamique.
    - Utilisation stratégique d’émojis adaptés au genre (ex : 🎭, 🖤, ⚙️).
    - Inclusion d’au moins 3 appels à l’action distincts adaptés au genre.
    - Éviter la répétition excessive de {artist} et {song}.
    - Maintien d’un ton cohérent : Dramatique, mystique.
    - Adaptation du style d’écriture aux conventions de YouTube.
    - Optimisation SEO avec mots-clés : "rock théâtral", "metal gothique", "indus".
    - Contenu exclusivement en {language}.
    **Exemple adapté** :
    - **Introduction** : "Depuis 2013, Silver Dust enchante avec un style rock théâtral théâtral et cinématographique, dévoilant leur nouveau titre Salve Regina ! 🎭"
    - **Description** : "Ce titre mêle riffs gothiques et sonorités industrielles, évoquant un mysticisme profond et une tension dramatique, comme un hymne à la rédemption. Une expérience sonore qui vous transporte dans un univers sombre et théâtral. 🖤"
    - **Contexte** : "Avec Salve Regina, Silver Dust poursuit son exploration d’un metal gothique dramatique, renforçant leur place unique dans la scène indus."
    - **Appels à l’action** : "Écoutez Salve Regina maintenant : [insert link]. Abonnez-vous pour plus de musique et de performances live ! Suivez Silver Dust sur Instagram et TikTok !"
    - **Section technique et crédits** : "Label : [collez l’email du label]. Booking Europe, Africa & North America : [collez l’email de booking]."
    - **Hashtags** : "#SilverDust #SalveRegina #RockThéâtral #MetalGothique #Indus"

    🔍 DIRECTIVES D’ADAPTATION
    **Matrice d’Adaptation au Genre Musical** :
    - **Rock théâtral** : Tons : Dramaturgique, Évocateur. Vocabulaire : théâtre, mystère, dramaturgie. Appels à l’action : "Plongez dans l’ombre", "Vibrez dans le mystère".
    - **Metal gothique** : Tons : Sombre, Mystique. Vocabulaire : gothique, mysticisme, riffs sombres. Appels à l’action : "Découvrez le mystère", "Ressentez l’obscurité".
    - **Indus** : Tons : Intense, Mécanique. Vocabulaire : indus, tension, textures mécaniques. Appels à l’action : "Plongez dans le chaos", "Vibrez avec l’intensité".

    **Analyse et Intégration de la Biographie** :
    - **Extraction du ton dominant** : Dramatique, mystique (style sombre et théâtral, avec une écriture évocatrice).
    - **Identification des thèmes récurrents** : Théâtralité, mysticisme, tension dramatique, univers cinématographique.
    - **Repérage des éléments distinctifs** : Approche théâtrale et cinématographique, mélange de metal gothique et indus.
    - **Application dans le contenu** :
      - Titres courts : 1 élément distinctif (ex : "Théâtre sombre").
      - Titres longs : 1-2 éléments biographiques (ex : "Univers théâtral").
      - Descriptions : 2-3 références au parcours ou aux thèmes (ex : "Mysticisme profond").
      - Description YouTube : Intégration structurée et complète.

    **Fusion Genre-Biographie** :
    - **Principe de base** : Le genre musical définit le cadre, la biographie apporte la personnalisation.
    - **Règle de cohérence** : En cas de contradiction, privilégier le ton de la biographie.
    - **Règle d’intensité** : Adapter le niveau d’expressivité à celui observé dans la biographie.
    - **Règle de spécificité** : Les éléments uniques de la biographie priment sur les généralités du genre.

    **Adaptation aux Plateformes** :
    - **Instagram/TikTok** : Privilégier titres courts, émojis stratégiques (🎭, 🖤, ⚙️).
    - **Facebook/Twitter** : Efficacité des titres longs et descriptions courtes avec ton dramatique.
    - **YouTube** : Description complète essentielle avec style reflétant la biographie.
    - **Streaming** : Adaptation des descriptions pour les plateformes d’écoute selon le genre.

    **Éléments Visuels par Genre** :
    - **Rock théâtral** : 🎭, 🎬, ⚡
    - **Metal gothique** : 🖤, 🕯️, 🌙
    - **Indus** : ⚙️, 🔩, 🔥

    📊 CRITÈRES DE QUALITÉ
    - Adaptation précise au genre musical spécifié.
    - Intégration naturelle des éléments biographiques.
    - Cohérence du ton entre le genre et la biographie.
    - Originalité et créativité dans les formulations.
    - Respect strict des contraintes de caractères.
    - Utilisation exclusive de la langue {language}.
    - Potentiel d’engagement et de conversion.
    - Optimisation pour le référencement (SEO).
    """

    try:
        # Appeler OpenAI pour générer les contenus
        logger.info("Calling OpenAI API")
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000
        )
        raw_response = response.choices[0].message.content
        logger.info(f"Raw response from OpenAI: {raw_response}")

        # Parsing robuste de la réponse d’OpenAI
        try:
            ad_data = json.loads(raw_response)
        except json.JSONDecodeError:
            logger.warning("OpenAI response is not a valid JSON, attempting manual parsing")
            ad_data = {
                "short_titles": [],
                "long_titles": [],
                "long_descriptions": [],
                "youtube_description_short": {"description": "", "character_count": 0},
                "youtube_description_full": {"description": "", "character_count": 0}
            }
            lines = raw_response.split("\n")
            current_section = None
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if "Short Titles" in line:
                    current_section = "short_titles"
                elif "Long Titles" in line:
                    current_section = "long_titles"
                elif "Long Descriptions" in line:
                    current_section = "long_descriptions"
                elif "YouTube Description" in line:
                    current_section = "youtube_description"
                elif "Short" in line and current_section == "youtube_description":
                    try:
                        desc = line.split(": ")[1].split(" (")[0]
                        char_count = int(line.split("(")[1].split(" /")[0])
                        ad_data["youtube_description_short"] = {"description": desc, "character_count": char_count}
                    except (IndexError, ValueError) as e:
                        logger.error(f"Error parsing YouTube short description: {e}")
                        ad_data["youtube_description_short"] = {"description": f"Plongez dans le mystère de {song} par {artist}! Écoutez maintenant!", "character_count": len(f"Plongez dans le mystère de {song} par {artist}! Écoutez maintenant!")}
                elif "Full" in line and current_section == "youtube_description":
                    try:
                        desc = line.split(": ")[1].split(" (")[0]
                        char_count = int(line.split("(")[1].split(" /")[0])
                        ad_data["youtube_description_full"] = {"description": desc, "character_count": char_count}
                    except (IndexError, ValueError) as e:
                        logger.error(f"Error parsing YouTube full description: {e}")
                        ad_data["youtube_description_full"] = {
                            "description": f"Depuis 2013, {artist} enchante avec un style {genres[0]} théâtral et cinématographique, dévoilant leur nouveau titre {song}! Ce titre mêle riffs gothiques et sonorités industrielles, évoquant un mysticisme profond et une tension dramatique. Écoutez {song} maintenant: {song_link}. Abonnez-vous pour plus de musique et de performances live! #{artist.replace(' ', '')} #{song.replace(' ', '')} #{genres[0].replace(' ', '')}",
                            "character_count": len(f"Depuis 2013, {artist} enchante avec un style {genres[0]} théâtral et cinématographique, dévoilant leur nouveau titre {song}! Ce titre mêle riffs gothiques et sonorités industrielles, évoquant un mysticisme profond et une tension dramatique. Écoutez {song} maintenant: {song_link}. Abonnez-vous pour plus de musique et de performances live! #{artist.replace(' ', '')} #{song.replace(' ', '')} #{genres[0].replace(' ', '')}")
                        }
                elif line.startswith("- ") and current_section in ["short_titles", "long_titles"]:
                    title = line[2:].split(" (")[0]
                    ad_data[current_section].append(title)
                elif line.startswith("- ") and current_section == "long_descriptions":
                    try:
                        desc = line[2:].split(" (")[0]
                        char_count = int(line.split("(")[1].split(" /")[0])
                        ad_data[current_section].append({"description": desc, "character_count": char_count})
                    except (IndexError, ValueError) as e:
                        logger.error(f"Error parsing long description: {e}")

        # Vérifier que les données générées sont cohérentes avec l’artiste et la chanson
        if not ad_data["short_titles"] or not ad_data["long_titles"] or not ad_data["long_descriptions"]:
            logger.error("OpenAI response did not contain expected data, generating fallback content")
            ad_data = {
                "short_titles": [
                    f"Salve Regina : mystère gothique ! (30 / 30)",
                    "Plongez dans l’ombre ! (22 / 30)",
                    f"Découvrez {song} ! (17 / 30)",
                    "Ambiance indus, écoutez ! (24 / 30)",
                    "Théâtre metal, vibrez ! (23 / 30)"
                ],
                "long_titles": [
                    f"Salve Regina : un voyage gothique ! (34 / 55)",
                    "Plongez dans un univers théâtral ! (34 / 55)",
                    f"Découvrez {song}, mystère indus ! (32 / 55)",
                    "Vibrez avec un son dramatique ! (30 / 55)",
                    "Metal gothique, écoutez ! (25 / 55)"
                ],
                "long_descriptions": [
                    {"description": f"{song} : riffs gothiques et mystère ! Écoutez ! (46 / 80)", "character_count": 46},
                    {"description": "Un son théâtral, plongez dans l’ombre ! (38 / 80)", "character_count": 38},
                    {"description": f"{song} : rédemption et tension ! Regardez ! (42 / 80)", "character_count": 42},
                    {"description": "Mysticisme indus, écoutez maintenant ! (37 / 80)", "character_count": 37},
                    {"description": "Ambiance dramatique ! Vibrez avec nous ! (39 / 80)", "character_count": 39}
                ],
                "youtube_description_short": ad_data["youtube_description_short"],
                "youtube_description_full": ad_data["youtube_description_full"]
            }

        # Mettre en cache le résultat
        logger.info(f"Caching OpenAI response for key: {cache_key}")
        cache[cache_key] = ad_data

        return ad_data

    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        cache.pop(cache_key, None)  # Invalider le cache en cas d’erreur
        return {"error": "Failed to generate ads"}, 500

# Point d’entrée pour Gunicorn
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
