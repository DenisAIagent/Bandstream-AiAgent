# Instructions d'Implémentation pour les Templates/UI et la Configuration de Déploiement

Ce document contient les instructions détaillées et le code complet pour implémenter les templates, l'interface utilisateur et la configuration de déploiement de l'application Band Stream.

## Partie 1: Templates et Interface Utilisateur

### Structure des Templates

```
templates/
├── index.html           # Page d'accueil avec formulaire
├── result.html          # Page de résultats
└── error.html           # Page d'erreur
```

### index.html

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Band Stream - Générateur de Campagnes Musicales</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root {
            --primary-color: #0ED894;
            --secondary-color: #6c757d;
            --dark-color: #343a40;
            --light-color: #f8f9fa;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            color: #333;
        }
        
        .navbar {
            background-color: var(--primary-color);
        }
        
        .navbar-brand {
            font-weight: bold;
            color: white !important;
        }
        
        .form-container {
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
            padding: 30px;
            margin-top: 30px;
            margin-bottom: 30px;
        }
        
        .form-step {
            display: none;
        }
        
        .form-step.active {
            display: block;
        }
        
        .step-indicator {
            display: flex;
            justify-content: space-between;
            margin-bottom: 30px;
        }
        
        .step {
            width: 30px;
            height: 30px;
            border-radius: 50%;
            background-color: var(--secondary-color);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
        }
        
        .step.active {
            background-color: var(--primary-color);
        }
        
        .step.completed {
            background-color: var(--primary-color);
        }
        
        .step-line {
            flex: 1;
            height: 2px;
            background-color: var(--secondary-color);
            margin: 15px 10px 0 10px;
        }
        
        .step-line.completed {
            background-color: var(--primary-color);
        }
        
        .btn-primary {
            background-color: var(--primary-color);
            border-color: var(--primary-color);
        }
        
        .btn-primary:hover {
            background-color: #0bc283;
            border-color: #0bc283;
        }
        
        .btn-secondary {
            background-color: var(--secondary-color);
            border-color: var(--secondary-color);
        }
        
        .form-label {
            font-weight: 600;
        }
        
        .required::after {
            content: " *";
            color: red;
        }
        
        .form-text {
            color: var(--secondary-color);
            font-size: 0.85rem;
        }
        
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(255, 255, 255, 0.8);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 9999;
            display: none;
        }
        
        .spinner-border {
            width: 3rem;
            height: 3rem;
            color: var(--primary-color);
        }
        
        .loading-text {
            margin-top: 15px;
            font-weight: 600;
            color: var(--dark-color);
        }
        
        .footer {
            background-color: var(--dark-color);
            color: white;
            padding: 20px 0;
            margin-top: 30px;
        }
    </style>
</head>
<body>
    <!-- Navbar -->
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container">
            <a class="navbar-brand" href="/">Band Stream</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link active" href="/">Accueil</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#about">À propos</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-lg-8">
                <div class="form-container">
                    <h1 class="text-center mb-4">Générateur de Campagnes Musicales</h1>
                    <p class="text-center mb-4">Créez des campagnes publicitaires personnalisées pour vos sorties musicales</p>
                    
                    <!-- Step Indicator -->
                    <div class="step-indicator">
                        <div class="step active" id="step-1">1</div>
                        <div class="step-line" id="line-1-2"></div>
                        <div class="step" id="step-2">2</div>
                        <div class="step-line" id="line-2-3"></div>
                        <div class="step" id="step-3">3</div>
                        <div class="step-line" id="line-3-4"></div>
                        <div class="step" id="step-4">4</div>
                    </div>
                    
                    <!-- Form -->
                    <form id="campaignForm">
                        <!-- Step 1: Basic Info -->
                        <div class="form-step active" id="step1">
                            <h3 class="mb-3">Informations de base</h3>
                            
                            <div class="mb-3">
                                <label for="artist" class="form-label required">Nom de l'artiste</label>
                                <input type="text" class="form-control" id="artist" required>
                                <div class="form-text">Entrez le nom complet de l'artiste ou du groupe</div>
                            </div>
                            
                            <div class="mb-3">
                                <label for="song" class="form-label required">Titre de la chanson</label>
                                <input type="text" class="form-control" id="song" required>
                                <div class="form-text">Entrez le titre exact de la chanson</div>
                            </div>
                            
                            <div class="mb-3">
                                <label for="style" class="form-label required">Genres musicaux</label>
                                <input type="text" class="form-control" id="style" required>
                                <div class="form-text">Entrez les genres séparés par des virgules (ex: rock, pop)</div>
                            </div>
                            
                            <div class="d-flex justify-content-end">
                                <button type="button" class="btn btn-primary" id="nextStep1">Suivant</button>
                            </div>
                        </div>
                        
                        <!-- Step 2: Release Info -->
                        <div class="form-step" id="step2">
                            <h3 class="mb-3">Informations sur la sortie</h3>
                            
                            <div class="mb-3">
                                <label for="promotion_type" class="form-label required">Type de promotion</label>
                                <select class="form-select" id="promotion_type" required>
                                    <option value="single">Single</option>
                                    <option value="clip" selected>Clip</option>
                                    <option value="album">Album</option>
                                    <option value="concert">Concert</option>
                                    <option value="tournée">Tournée</option>
                                </select>
                                <div class="form-text">Sélectionnez le type de promotion pour votre campagne</div>
                            </div>
                            
                            <div class="mb-3" id="album_name_container" style="display: none;">
                                <label for="album_name" class="form-label">Nom de l'album</label>
                                <input type="text" class="form-control" id="album_name">
                                <div class="form-text">Entrez le nom de l'album (uniquement si vous avez sélectionné "Album")</div>
                            </div>
                            
                            <div class="mb-3">
                                <label for="song_url" class="form-label">URL de la chanson</label>
                                <input type="url" class="form-control" id="song_url">
                                <div class="form-text">Entrez l'URL de la chanson (YouTube, Spotify, etc.)</div>
                            </div>
                            
                            <div class="d-flex justify-content-between">
                                <button type="button" class="btn btn-secondary" id="prevStep2">Précédent</button>
                                <button type="button" class="btn btn-primary" id="nextStep2">Suivant</button>
                            </div>
                        </div>
                        
                        <!-- Step 3: Content Style -->
                        <div class="form-step" id="step3">
                            <h3 class="mb-3">Style du contenu</h3>
                            
                            <div class="mb-3">
                                <label for="language" class="form-label required">Langue</label>
                                <select class="form-select" id="language" required>
                                    <option value="français" selected>Français</option>
                                    <option value="anglais">Anglais</option>
                                    <option value="espagnol">Espagnol</option>
                                </select>
                                <div class="form-text">Sélectionnez la langue pour votre campagne</div>
                            </div>
                            
                            <div class="mb-3">
                                <label for="tone" class="form-label">Ton</label>
                                <select class="form-select" id="tone">
                                    <option value="engageant" selected>Engageant</option>
                                    <option value="poétique">Poétique</option>
                                    <option value="humoristique">Humoristique</option>
                                    <option value="sérieux">Sérieux</option>
                                    <option value="mystérieux">Mystérieux</option>
                                    <option value="énergique">Énergique</option>
                                </select>
                                <div class="form-text">Sélectionnez le ton pour votre campagne</div>
                            </div>
                            
                            <div class="d-flex justify-content-between">
                                <button type="button" class="btn btn-secondary" id="prevStep3">Précédent</button>
                                <button type="button" class="btn btn-primary" id="nextStep3">Suivant</button>
                            </div>
                        </div>
                        
                        <!-- Step 4: Additional Info -->
                        <div class="form-step" id="step4">
                            <h3 class="mb-3">Informations supplémentaires</h3>
                            
                            <div class="mb-3">
                                <label for="bio" class="form-label">Biographie de l'artiste</label>
                                <textarea class="form-control" id="bio" rows="3"></textarea>
                                <div class="form-text">Entrez une courte biographie de l'artiste (facultatif)</div>
                            </div>
                            
                            <div class="mb-3">
                                <label for="lyrics" class="form-label">Paroles de la chanson</label>
                                <textarea class="form-control" id="lyrics" rows="3"></textarea>
                                <div class="form-text">Entrez les paroles de la chanson (facultatif)</div>
                            </div>
                            
                            <div class="d-flex justify-content-between">
                                <button type="button" class="btn btn-secondary" id="prevStep4">Précédent</button>
                                <button type="submit" class="btn btn-primary" id="submitForm">Générer la campagne</button>
                            </div>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    </div>
    
    <!-- About Section -->
    <section id="about" class="py-5 bg-light">
        <div class="container">
            <div class="row">
                <div class="col-lg-8 mx-auto text-center">
                    <h2 class="mb-4">À propos de Band Stream</h2>
                    <p class="lead">
                        Band Stream est une plateforme innovante qui utilise l'intelligence artificielle pour générer des campagnes publicitaires personnalisées pour les artistes musicaux. Notre technologie combine des données de Chartmetric, YouTube, MusicBrainz et OpenAI pour créer du contenu marketing optimisé pour chaque artiste et genre musical.
                    </p>
                </div>
            </div>
        </div>
    </section>
    
    <!-- Footer -->
    <footer class="footer">
        <div class="container">
            <div class="row">
                <div class="col-md-6">
                    <h5>Band Stream</h5>
                    <p>Propulsez votre musique avec l'IA</p>
                </div>
                <div class="col-md-6 text-md-end">
                    <p>&copy; 2025 Band Stream. Tous droits réservés.</p>
                </div>
            </div>
        </div>
    </footer>
    
    <!-- Loading Overlay -->
    <div class="loading-overlay" id="loadingOverlay">
        <div class="spinner-border" role="status">
            <span class="visually-hidden">Chargement...</span>
        </div>
        <p class="loading-text">Génération de votre campagne en cours...</p>
        <p class="loading-subtext">Cela peut prendre jusqu'à 30 secondes</p>
    </div>
    
    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    
    <!-- Form Handling Script -->
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            // Form Steps Navigation
            const steps = ['step1', 'step2', 'step3', 'step4'];
            let currentStep = 0;
            
            // Step Indicators
            const stepIndicators = [
                document.getElementById('step-1'),
                document.getElementById('step-2'),
                document.getElementById('step-3'),
                document.getElementById('step-4')
            ];
            
            const stepLines = [
                document.getElementById('line-1-2'),
                document.getElementById('line-2-3'),
                document.getElementById('line-3-4')
            ];
            
            // Show a specific step
            function showStep(stepIndex) {
                // Hide all steps
                document.querySelectorAll('.form-step').forEach(step => {
                    step.classList.remove('active');
                });
                
                // Show the current step
                document.getElementById(steps[stepIndex]).classList.add('active');
                
                // Update step indicators
                stepIndicators.forEach((indicator, index) => {
                    if (index < stepIndex) {
                        indicator.classList.add('completed');
                        indicator.classList.remove('active');
                    } else if (index === stepIndex) {
                        indicator.classList.add('active');
                        indicator.classList.remove('completed');
                    } else {
                        indicator.classList.remove('active');
                        indicator.classList.remove('completed');
                    }
                });
                
                // Update step lines
                stepLines.forEach((line, index) => {
                    if (index < stepIndex) {
                        line.classList.add('completed');
                    } else {
                        line.classList.remove('completed');
                    }
                });
                
                currentStep = stepIndex;
            }
            
            // Validate current step
            function validateStep(stepIndex) {
                if (stepIndex === 0) {
                    const artist = document.getElementById('artist').value;
                    const song = document.getElementById('song').value;
                    const style = document.getElementById('style').value;
                    
                    if (!artist || !song || !style) {
                        alert('Veuillez remplir tous les champs obligatoires.');
                        return false;
                    }
                } else if (stepIndex === 1) {
                    const promotionType = document.getElementById('promotion_type').value;
                    
                    if (!promotionType) {
                        alert('Veuillez sélectionner un type de promotion.');
                        return false;
                    }
                    
                    if (promotionType === 'album') {
                        const albumName = document.getElementById('album_name').value;
                        if (!albumName) {
                            alert('Veuillez entrer le nom de l\'album.');
                            return false;
                        }
                    }
                } else if (stepIndex === 2) {
                    const language = document.getElementById('language').value;
                    
                    if (!language) {
                        alert('Veuillez sélectionner une langue.');
                        return false;
                    }
                }
                
                return true;
            }
            
            // Next button event listeners
            document.getElementById('nextStep1').addEventListener('click', function() {
                if (validateStep(0)) {
                    showStep(1);
                }
            });
            
            document.getElementById('nextStep2').addEventListener('click', function() {
                if (validateStep(1)) {
                    showStep(2);
                }
            });
            
            document.getElementById('nextStep3').addEventListener('click', function() {
                if (validateStep(2)) {
                    showStep(3);
                }
            });
            
            // Previous button event listeners
            document.getElementById('prevStep2').addEventListener('click', function() {
                showStep(0);
            });
            
            document.getElementById('prevStep3').addEventListener('click', function() {
                showStep(1);
            });
            
            document.getElementById('prevStep4').addEventListener('click', function() {
                showStep(2);
            });
            
            // Show/hide album name field based on promotion type
            document.getElementById('promotion_type').addEventListener('change', function() {
                const albumNameContainer = document.getElementById('album_name_container');
                if (this.value === 'album') {
                    albumNameContainer.style.display = 'block';
                } else {
                    albumNameContainer.style.display = 'none';
                }
            });
            
            // Form submission
            document.getElementById('campaignForm').addEventListener('submit', async function(event) {
                event.preventDefault();
                
                // Show loading overlay
                document.getElementById('loadingOverlay').style.display = 'flex';
                
                // Get form data
                const artist = document.getElementById('artist').value;
                const song = document.getElementById('song').value;
                const style = document.getElementById('style').value;
                const promotionType = document.getElementById('promotion_type').value;
                const albumName = document.getElementById('album_name').value;
                const songUrl = document.getElementById('song_url').value;
                const language = document.getElementById('language').value;
                const tone = document.getElementById('tone').value;
                const bio = document.getElementById('bio').value;
                const lyrics = document.getElementById('lyrics').value;
                
                // Convert style to genres array
                const genres = style.split(',').map(s => s.trim());
                
                // Prepare data object
                const data = {
                    artist: artist,
                    song: song,
                    genres: genres,
                    promotion_type: promotionType,
                    language: language,
                    tone: tone,
                    bio: bio,
                    song_lyrics: lyrics,
                    song_link: songUrl
                };
                
                // Add album name if applicable
                if (promotionType === 'album' && albumName) {
                    data.album_name = albumName;
                }
                
                try {
                    // Send data to server
                    const response = await fetch('/generate_campaign', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(data)
                    });
                    
                    // Hide loading overlay
                    document.getElementById('loadingOverlay').style.display = 'none';
                    
                    if (!response.ok) {
                        // Handle error response
                        const errorData = await response.json();
                        throw new Error(errorData.error || 'Échec de la génération de la campagne');
                    }
                    
                    // Get response HTML and replace page content
                    const result = await response.text();
                    document.body.innerHTML = result;
                    
                    // Scroll to top
                    window.scrollTo(0, 0);
                } catch (error) {
                    // Hide loading overlay
                    document.getElementById('loadingOverlay').style.display = 'none';
                    
                    // Show error message
                    alert('Erreur : ' + error.message);
                }
            });
        });
    </script>
</body>
</html>
```

### result.html

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Résultats de la Campagne - Band Stream</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root {
            --primary-color: #0ED894;
            --secondary-color: #6c757d;
            --dark-color: #343a40;
            --light-color: #f8f9fa;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            color: #333;
        }
        
        .navbar {
            background-color: var(--primary-color);
        }
        
        .navbar-brand {
            font-weight: bold;
            color: white !important;
        }
        
        .result-container {
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
            padding: 30px;
            margin-top: 30px;
            margin-bottom: 30px;
        }
        
        .section-title {
            color: var(--primary-color);
            border-bottom: 2px solid var(--primary-color);
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        
        .card {
            margin-bottom: 20px;
            border: none;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.05);
        }
        
        .card-header {
            background-color: var(--primary-color);
            color: white;
            font-weight: 600;
        }
        
        .btn-primary {
            background-color: var(--primary-color);
            border-color: var(--primary-color);
        }
        
        .btn-primary:hover {
            background-color: #0bc283;
            border-color: #0bc283;
        }
        
        .artist-info {
            display: flex;
            align-items: center;
            margin-bottom: 30px;
        }
        
        .artist-image {
            width: 150px;
            height: 150px;
            border-radius: 50%;
            object-fit: cover;
            margin-right: 20px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.2);
        }
        
        .artist-details h2 {
            margin-bottom: 5px;
            color: var(--dark-color);
        }
        
        .artist-details p {
            margin-bottom: 5px;
            color: var(--secondary-color);
        }
        
        .badge {
            margin-right: 5px;
            margin-bottom: 5px;
            background-color: var(--primary-color);
        }
        
        .footer {
            background-color: var(--dark-color);
            color: white;
            padding: 20px 0;
            margin-top: 30px;
        }
        
        .copy-btn {
            cursor: pointer;
            padding: 5px 10px;
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            font-size: 0.8rem;
            margin-left: 10px;
        }
        
        .copy-btn:hover {
            background-color: #e9ecef;
        }
        
        .copy-success {
            color: var(--primary-color);
            font-size: 0.8rem;
            margin-left: 10px;
            display: none;
        }
        
        .youtube-preview {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
        }
        
        .youtube-title {
            font-weight: bold;
            font-size: 1.2rem;
            margin-bottom: 10px;
        }
        
        .youtube-description {
            white-space: pre-line;
            font-size: 0.9rem;
            color: #666;
        }
    </style>
</head>
<body>
    <!-- Navbar -->
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container">
            <a class="navbar-brand" href="/">Band Stream</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="/">Accueil</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#about">À propos</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-lg-10">
                <div class="result-container">
                    <h1 class="text-center mb-4">Votre Campagne est Prête !</h1>
                    
                    <!-- Artist Info -->
                    <div class="artist-info">
                        <img src="{{ analysis.artist_image_url }}" alt="{{ analysis.artist }}" class="artist-image">
                        <div class="artist-details">
                            <h2>{{ analysis.artist }}</h2>
                            <p><strong>Chanson :</strong> {{ analysis.song }}</p>
                            <p><strong>Styles :</strong> 
                                {% for style in analysis.styles %}
                                <span class="badge bg-primary">{{ style }}</span>
                                {% endfor %}
                            </p>
                            <p><strong>Explication :</strong> {{ analysis.analysis_explanation }}</p>
                        </div>
                    </div>
                    
                    <!-- Short Titles -->
                    <div class="mb-5">
                        <h3 class="section-title">Titres Courts</h3>
                        <div class="row">
                            {% for title in ads.short_titles %}
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-body">
                                        <p class="card-text">{{ title }}</p>
                                        <button class="copy-btn" onclick="copyToClipboard(this, '{{ title }}')">Copier</button>
                                        <span class="copy-success">Copié !</span>
                                    </div>
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                    
                    <!-- Long Titles -->
                    <div class="mb-5">
                        <h3 class="section-title">Titres Longs</h3>
                        <div class="row">
                            {% for title in ads.long_titles %}
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-body">
                                        <p class="card-text">{{ title }}</p>
                                        <button class="copy-btn" onclick="copyToClipboard(this, '{{ title }}')">Copier</button>
                                        <span class="copy-success">Copié !</span>
                                    </div>
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                    
                    <!-- Long Descriptions -->
                    <div class="mb-5">
                        <h3 class="section-title">Descriptions</h3>
                        <div class="row">
                            {% for desc in ads.long_descriptions %}
                            <div class="col-md-6">
                                <div class="card">
                                    <div class="card-body">
                                        <p class="card-text">{{ desc.description }}</p>
                                        <small class="text-muted">{{ desc.character_count }} caractères</small>
                                        <button class="copy-btn" onclick="copyToClipboard(this, '{{ desc.description }}')">Copier</button>
                                        <span class="copy-success">Copié !</span>
                                    </div>
                                </div>
                            </div>
                            {% endfor %}
                        </div>
                    </div>
                    
                    <!-- YouTube Description -->
                    <div class="mb-5">
                        <h3 class="section-title">Description YouTube</h3>
                        
                        <!-- Short Description -->
                        <div class="card mb-3">
                            <div class="card-header">Description Courte</div>
                            <div class="card-body">
                                <p class="card-text">{{ ads.youtube_description_short.description }}</p>
                                <small class="text-muted">{{ ads.youtube_description_short.character_count }} caractères</small>
                                <button class="copy-btn" onclick="copyToClipboard(this, '{{ ads.youtube_description_short.description }}')">Copier</button>
                                <span class="copy-success">Copié !</span>
                            </div>
                        </div>
                        
                        <!-- Full Description -->
                        <div class="card">
                            <div class="card-header">Description Complète</div>
                            <div class="card-body">
                                <div class="youtube-preview">
                                    <div class="youtube-title">{{ analysis.artist }} - {{ analysis.song }}</div>
                                    <div class="youtube-description">{{ ads.youtube_description_full.description }}</div>
                                </div>
                                <div class="mt-3">
                                    <small class="text-muted">{{ ads.youtube_description_full.character_count }} caractères</small>
                                    <button class="copy-btn" onclick="copyToClipboard(this, '{{ ads.youtube_description_full.description }}')">Copier</button>
                                    <span class="copy-success">Copié !</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Strategy -->
                    <div class="mb-5">
                        <h3 class="section-title">Stratégie de Campagne</h3>
                        <div class="card">
                            <div class="card-body">
                                <p><strong>Public cible :</strong> {{ strategy.target_audience }}</p>
                                <p><strong>Canaux recommandés :</strong></p>
                                <ul>
                                    {% for channel in strategy.channels %}
                                    <li>{{ channel }} ({{ (strategy.budget_allocation[channel] * 100)|int }}% du budget)</li>
                                    {% endfor %}
                                </ul>
                                <p><strong>Artistes similaires :</strong></p>
                                <div>
                                    {% for artist in analysis.lookalike_artists %}
                                    <span class="badge bg-secondary">{{ artist }}</span>
                                    {% endfor %}
                                </div>
                                <p class="mt-3"><strong>Tendances à exploiter :</strong></p>
                                <div>
                                    {% for trend in analysis.trends %}
                                    <span class="badge bg-secondary">{{ trend }}</span>
                                    {% endfor %}
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Action Buttons -->
                    <div class="text-center mt-5">
                        <a href="/" class="btn btn-primary">Créer une nouvelle campagne</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Footer -->
    <footer class="footer">
        <div class="container">
            <div class="row">
                <div class="col-md-6">
                    <h5>Band Stream</h5>
                    <p>Propulsez votre musique avec l'IA</p>
                </div>
                <div class="col-md-6 text-md-end">
                    <p>&copy; 2025 Band Stream. Tous droits réservés.</p>
                </div>
            </div>
        </div>
    </footer>
    
    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    
    <!-- Copy to Clipboard Script -->
    <script>
        function copyToClipboard(button, text) {
            // Create a temporary textarea element
            const textarea = document.createElement('textarea');
            textarea.value = text;
            document.body.appendChild(textarea);
            
            // Select and copy the text
            textarea.select();
            document.execCommand('copy');
            
            // Remove the temporary textarea
            document.body.removeChild(textarea);
            
            // Show success message
            const successElement = button.nextElementSibling;
            successElement.style.display = 'inline';
            
            // Hide success message after 2 seconds
            setTimeout(() => {
                successElement.style.display = 'none';
            }, 2000);
        }
    </script>
</body>
</html>
```

### error.html

```html
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Erreur - Band Stream</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root {
            --primary-color: #0ED894;
            --secondary-color: #6c757d;
            --dark-color: #343a40;
            --light-color: #f8f9fa;
            --danger-color: #dc3545;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            color: #333;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
        }
        
        .navbar {
            background-color: var(--primary-color);
        }
        
        .navbar-brand {
            font-weight: bold;
            color: white !important;
        }
        
        .error-container {
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
            padding: 30px;
            margin-top: 50px;
            margin-bottom: 50px;
            text-align: center;
        }
        
        .error-icon {
            font-size: 5rem;
            color: var(--danger-color);
            margin-bottom: 20px;
        }
        
        .error-title {
            color: var(--danger-color);
            font-size: 2rem;
            margin-bottom: 20px;
        }
        
        .error-message {
            margin-bottom: 30px;
            font-size: 1.1rem;
        }
        
        .btn-primary {
            background-color: var(--primary-color);
            border-color: var(--primary-color);
        }
        
        .btn-primary:hover {
            background-color: #0bc283;
            border-color: #0bc283;
        }
        
        .footer {
            background-color: var(--dark-color);
            color: white;
            padding: 20px 0;
            margin-top: auto;
        }
        
        .error-details {
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 15px;
            margin-top: 20px;
            text-align: left;
            font-family: monospace;
            font-size: 0.9rem;
            color: #666;
            max-height: 200px;
            overflow-y: auto;
        }
    </style>
</head>
<body>
    <!-- Navbar -->
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container">
            <a class="navbar-brand" href="/">Band Stream</a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    <li class="nav-item">
                        <a class="nav-link" href="/">Accueil</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="#about">À propos</a>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <div class="container flex-grow-1">
        <div class="row justify-content-center">
            <div class="col-lg-8">
                <div class="error-container">
                    <div class="error-icon">
                        <i class="bi bi-exclamation-triangle-fill"></i>
                        ❌
                    </div>
                    <h1 class="error-title">Une erreur est survenue</h1>
                    <p class="error-message">
                        Nous n'avons pas pu générer votre campagne en raison d'une erreur.
                        Veuillez réessayer ou contacter notre support si le problème persiste.
                    </p>
                    <div class="error-details">
                        {{ error }}
                    </div>
                    <div class="mt-4">
                        <a href="/" class="btn btn-primary">Retour à l'accueil</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Footer -->
    <footer class="footer">
        <div class="container">
            <div class="row">
                <div class="col-md-6">
                    <h5>Band Stream</h5>
                    <p>Propulsez votre musique avec l'IA</p>
                </div>
                <div class="col-md-6 text-md-end">
                    <p>&copy; 2025 Band Stream. Tous droits réservés.</p>
                </div>
            </div>
        </div>
    </footer>
    
    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
```

## Partie 2: Configuration de Déploiement

### Structure des Fichiers de Déploiement

```
/
├── .env                  # Variables d'environnement (non versionné)
├── .env.example          # Exemple de variables d'environnement
├── .gitignore            # Fichiers à ignorer dans Git
├── docker-compose.yml    # Configuration Docker pour le développement local
└── railway.json          # Configuration Railway
```

### .env.example

```
# API Keys
OPENAI_API_KEY=your_openai_api_key
YOUTUBE_API_KEY=your_youtube_api_key
CHARTMETRIC_REFRESH_TOKEN=your_chartmetric_refresh_token

# Service Configuration
DEBUG=False
LOG_LEVEL=INFO
PORT=8080

# Cache Configuration
CACHE_TTL=86400
CACHE_MAXSIZE=100

# OpenAI Configuration
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=2000

# MusicBrainz Configuration
MUSICBRAINZ_APP_NAME=band-stream
MUSICBRAINZ_VERSION=1.0
MUSICBRAINZ_CONTACT=your-email@example.com
```

### .gitignore

```
# Environment variables
.env

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Logs
logs/
*.log

# OS specific
.DS_Store
Thumbs.db
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  chartmetric_service:
    build: ./chartmetric_service
    ports:
      - "8081:8080"
    env_file:
      - .env
    volumes:
      - ./chartmetric_service:/app
    restart: unless-stopped

  campaign_analyst:
    build: ./campaign_analyst
    ports:
      - "8082:8080"
    env_file:
      - .env
    volumes:
      - ./campaign_analyst:/app
    restart: unless-stopped

  campaign_optimizer:
    build: ./campaign_optimizer
    ports:
      - "8083:8080"
    env_file:
      - .env
    volumes:
      - ./campaign_optimizer:/app
    restart: unless-stopped

  marketing_agent:
    build: ./marketing_agent
    ports:
      - "8084:8080"
    env_file:
      - .env
    volumes:
      - ./marketing_agent:/app
    restart: unless-stopped

  campaign_supervisor:
    build: ./campaign_supervisor
    ports:
      - "8080:8080"
    env_file:
      - .env
    volumes:
      - ./campaign_supervisor:/app
    depends_on:
      - chartmetric_service
      - campaign_analyst
      - campaign_optimizer
      - marketing_agent
    restart: unless-stopped
```

### railway.json

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn campaign_supervisor.campaign_supervisor:asgi_app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### Dockerfile (pour chaque service)

Exemple pour le service Chartmetric :

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app.py"]
```

## Instructions de Déploiement sur Railway

### 1. Préparation des Dépôts GitHub

1. Créez un dépôt GitHub pour chaque service :
   - `band-stream-chartmetric-service`
   - `band-stream-campaign-analyst`
   - `band-stream-campaign-optimizer`
   - `band-stream-marketing-agent`
   - `band-stream-campaign-supervisor`

2. Organisez les fichiers selon la structure décrite dans les instructions d'implémentation pour chaque service.

### 2. Configuration des Variables d'Environnement

1. Connectez-vous à Railway (https://railway.app/).
2. Créez un nouveau projet pour Band Stream.
3. Pour chaque service, ajoutez les variables d'environnement nécessaires :

**Variables communes à tous les services :**
- `DEBUG`: "False" pour la production
- `LOG_LEVEL`: "INFO" pour la production
- `PORT`: "8080" (Railway remplacera cette valeur)

**Variables spécifiques :**
- Chartmetric Service : `CHARTMETRIC_REFRESH_TOKEN`
- Campaign Analyst : `OPENAI_API_KEY`, `YOUTUBE_API_KEY`
- Campaign Optimizer : `YOUTUBE_API_KEY`, `CHARTMETRIC_REFRESH_TOKEN`
- Marketing Agent : `OPENAI_API_KEY`
- Campaign Supervisor : Aucune variable spécifique

### 3. Déploiement des Services

1. Déployez d'abord les services auxiliaires :
   - Chartmetric Service
   - Campaign Analyst
   - Campaign Optimizer
   - Marketing Agent

2. Une fois ces services déployés, notez leurs URLs :
   - `https://chartmetric-service-production.up.railway.app`
   - `https://analyst-production.up.railway.app`
   - `https://optimizer-production.up.railway.app`
   - `https://marketing-agent-production.up.railway.app`

3. Mettez à jour le fichier `campaign_supervisor.py` avec ces URLs.

4. Déployez enfin le Campaign Supervisor.

### 4. Vérification du Déploiement

1. Accédez à l'URL du Campaign Supervisor : `https://bandstream.up.railway.app`
2. Vérifiez que la page d'accueil s'affiche correctement.
3. Testez la génération d'une campagne avec les données suivantes :
   - Artiste : "Silver Dust"
   - Chanson : "Salve Regina"
   - Genres : "metal symphonique, metal indus"
   - Type de promotion : "clip"
   - Langue : "français"
   - Ton : "engageant"

### 5. Surveillance et Maintenance

1. Configurez des alertes dans Railway pour être notifié en cas de problème.
2. Surveillez les logs de chaque service pour détecter d'éventuelles erreurs.
3. Mettez en place un système de sauvegarde régulière des données importantes.

## Bonnes Pratiques pour le Développement Futur

1. **Gestion des Versions :**
   - Utilisez le versionnage sémantique pour les releases.
   - Documentez les changements dans un fichier CHANGELOG.md.

2. **Tests :**
   - Écrivez des tests unitaires pour chaque service.
   - Mettez en place des tests d'intégration pour vérifier les interactions entre services.
   - Utilisez un environnement de staging pour tester les nouvelles fonctionnalités.

3. **Documentation :**
   - Maintenez une documentation à jour pour chaque service.
   - Documentez les API avec des outils comme Swagger ou ReDoc.
   - Créez des guides d'utilisation pour les utilisateurs finaux.

4. **Sécurité :**
   - Effectuez des audits de sécurité réguliers.
   - Mettez à jour les dépendances pour corriger les vulnérabilités.
   - Utilisez HTTPS pour toutes les communications.

5. **Performance :**
   - Optimisez les requêtes aux API externes.
   - Améliorez les stratégies de cache.
   - Surveillez les temps de réponse et optimisez les goulots d'étranglement.

6. **Évolutivité :**
   - Concevez les services pour qu'ils puissent évoluer indépendamment.
   - Utilisez des interfaces bien définies entre les services.
   - Prévoyez des mécanismes de migration des données.
