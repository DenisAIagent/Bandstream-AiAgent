# Band Stream Crew IA Agent

## Vue d'ensemble

Band Stream Crew IA Agent est une application modulaire sophistiquée conçue pour générer des campagnes marketing optimisées pour les artistes musicaux. Ce système utilise l'intelligence artificielle pour analyser les tendances du marché musical, identifier les artistes similaires, et créer des annonces publicitaires efficaces qui respectent les règles de Google Ads.

## Architecture du système

Le système est composé de 5 agents autonomes, chacun hébergé dans son propre conteneur Docker, fonctionnant de manière asynchrone pour maximiser l'efficacité et la réactivité :

1. **MAIN** - Interface utilisateur
   * Point d'entrée principal du système
   * Gère les interactions avec l'utilisateur en temps réel
   * Coordonne les flux de travail entre les différents agents
   * Implémente des websockets pour les mises à jour en direct

2. **SUPERVISOR** - Chef de projet
   * Supervise l'ensemble du processus de génération de campagne
   * Assure la cohérence entre les différentes étapes
   * Valide les résultats avant leur présentation à l'utilisateur
   * Gère les files d'attente de tâches et la distribution du travail

3. **ANALYST** - Recherche d'insights
   * Collecte et analyse les données sur les artistes et les tendances musicales
   * Utilise les APIs externes pour obtenir des informations pertinentes
   * Génère des insights stratégiques pour orienter la création de campagnes
   * Exécute des tâches d'analyse parallèles pour accélérer le traitement

4. **MARKETING** - Rédaction d'annonces
   * Crée des textes publicitaires adaptés au style de l'artiste
   * Optimise les messages en fonction des tendances identifiées
   * Assure la conformité avec les bonnes pratiques marketing
   * Génère plusieurs variantes de contenu simultanément

5. **OPTIMIZER** - Optimisation
   * Affine les annonces pour maximiser leur efficacité
   * Vérifie la conformité avec les règles de Google Ads
   * Propose des améliorations basées sur les performances prévues
   * Effectue des tests A/B automatisés pour affiner les résultats

## Communication entre les agents

Les agents communiquent via une API Flask centrale avec un système de messagerie asynchrone qui :
* Facilite l'échange de données entre les différents modules sans blocage
* Maintient la cohérence des informations à travers le système
* Permet une architecture découplée où chaque agent peut évoluer indépendamment
* Utilise des files d'attente Redis pour la gestion des tâches asynchrones
* Implémente des websockets pour les communications en temps réel
* Gère les retries automatiques en cas d'échec de communication
* Permet l'exécution parallèle de multiples tâches pour optimiser les performances

## Sources de données

Le système s'appuie sur plusieurs APIs externes pour obtenir des données pertinentes, toutes intégrées avec un traitement asynchrone pour optimiser les performances :

* **Spotify API** - Pour accéder aux métadonnées des artistes, aux statistiques d'écoute et aux caractéristiques musicales
  * Utilisation des endpoints `/artists`, `/audio-features` et `/recommendations`
  * Extraction des données de popularité, genres et artistes similaires
  * Analyse des caractéristiques audio (danceability, energy, tempo)

* **Deezer API** - Pour obtenir des informations complémentaires sur les artistes et leur audience
  * Endpoints `/artist` et `/chart` pour les données de classement
  * Analyse des fans et de leur répartition géographique
  * Statistiques d'écoute par plateforme

* **YouTube/SerpApi** - Pour analyser la présence des artistes sur YouTube et leur visibilité en ligne
  * Extraction des statistiques de vidéos (vues, likes, commentaires)
  * Analyse des tendances de recherche liées à l'artiste
  * Évaluation de l'engagement du public sur les contenus

* **Google Trends** - Pour identifier les tendances actuelles liées aux genres musicaux et aux artistes
  * Données d'intérêt au fil du temps
  * Comparaisons régionales et saisonnières
  * Requêtes associées et sujets connexes

* **Chartmetrics** - Pour des analyses approfondies de performance et de positionnement
  * Suivi des performances sur les plateformes de streaming
  * Analyse comparative avec les concurrents
  * Métriques d'engagement social et de croissance d'audience
  * Données démographiques détaillées des auditeurs

## Fonctionnalités principales

### Analyse de marché
* Identification des artistes similaires à l'artiste cible
* Analyse des tendances actuelles dans le genre musical concerné
* Évaluation de la concurrence et des opportunités de marché

### Génération de contenu
* Création d'annonces publicitaires adaptées au style de l'artiste
* Rédaction de textes optimisés pour différentes plateformes
* Suggestions visuelles cohérentes avec l'identité de l'artiste

### Optimisation des campagnes
* Conformité avec les règles de Google Ads
* Maximisation du taux de conversion potentiel
* Recommandations pour le ciblage d'audience

## Flux de travail typique

1. L'utilisateur soumet une demande via l'interface MAIN
2. Le SUPERVISOR établit un plan de travail et distribue les tâches
3. L'ANALYST collecte et analyse les données pertinentes
4. Le MARKETING génère des propositions d'annonces
5. L'OPTIMIZER affine et optimise les annonces
6. Le SUPERVISOR valide les résultats
7. MAIN présente les campagnes finalisées à l'utilisateur

## Avantages du système

* **Automatisation** - Réduit considérablement le temps nécessaire pour créer des campagnes marketing efficaces
* **Intelligence** - Utilise l'IA pour identifier les tendances et opportunités que les humains pourraient manquer
* **Cohérence** - Assure une qualité constante dans toutes les campagnes générées
* **Conformité** - Garantit que toutes les annonces respectent les règles des plateformes publicitaires
* **Évolutivité** - L'architecture modulaire permet d'ajouter facilement de nouvelles fonctionnalités

## Prérequis techniques

* Docker et Docker Compose pour l'exécution des conteneurs
* Accès aux APIs (Spotify, Deezer, YouTube/SerpApi, Google Trends)
* Connexion Internet stable pour les communications entre agents et APIs externes

## Installation et déploiement

Le système utilise Docker pour faciliter le déploiement :

```bash
# Cloner le dépôt
git clone https://github.com/votre-organisation/band-stream-crew.git

# Accéder au répertoire
cd band-stream-crew

# Configurer les variables d'environnement
cp .env.example .env
# Éditer le fichier .env avec vos clés d'API

# Lancer les conteneurs
docker-compose up -d
```

## Utilisation

Une fois le système déployé, accédez à l'interface utilisateur via :

```
http://localhost:8080
```

Suivez les instructions à l'écran pour :
1. Saisir les informations sur l'artiste
2. Définir les objectifs de la campagne
3. Spécifier les contraintes (budget, plateformes, etc.)
4. Lancer la génération de campagne
5. Examiner et exporter les résultats

## Maintenance et mise à jour

Le système est conçu pour être facilement maintenu et mis à jour :

```bash
# Mettre à jour le code source
git pull

# Reconstruire les conteneurs avec les dernières modifications
docker-compose build

# Redémarrer les services
docker-compose down
docker-compose up -d
```

## Dépannage

Problèmes courants et solutions :

* **Erreurs d'API** - Vérifiez la validité de vos clés d'API dans le fichier .env
* **Problèmes de communication entre agents** - Assurez-vous que tous les conteneurs sont en cours d'exécution
* **Résultats incomplets** - Vérifiez les journaux pour identifier l'agent qui rencontre des difficultés

## Contribution

Les contributions au projet sont les bienvenues. Veuillez suivre ces étapes :

1. Forker le dépôt
2. Créer une branche pour votre fonctionnalité
3. Soumettre une pull request avec une description détaillée

## Licence

Ce projet est sous licence propriétaire. Voir le fichier LICENSE pour plus de détails.

---

Développé avec ❤️ par Band Stream
