@app.route('/generate_campaign', methods=['POST'])
def generate_campaign():
    if request.method == 'POST':
        # Récupérer les données du formulaire
        artist = request.form.get('artist', '')
        song = request.form.get('song', '')
        genres = request.form.getlist('genres')
        language = request.form.get('language', 'français')
        promotion_type = request.form.get('promotion_type', 'sortie')
        lyrics = request.form.get('lyrics', '')
        bio = request.form.get('bio', '')
        song_link = request.form.get('song_link', '')

        # Générer un ID unique pour la campagne
        campaign_id = str(uuid.uuid4())
        
        # Créer un dictionnaire pour stocker les données de la campagne
        campaign = {
            'id': campaign_id,
            'artist': artist,
            'song': song,
            'genres': genres,
            'language': language,
            'promotion_type': promotion_type,
            'lyrics': lyrics,
            'bio': bio,
            'song_link': song_link,
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'pending',
            'progress': {
                'chartmetric': 'pending',
                'analyst': 'pending',
                'marketing': 'pending',
                'optimizer': 'pending'
            }
        }
        
        # Stocker la campagne dans la session
        if 'campaigns' not in session:
            session['campaigns'] = {}
        session['campaigns'][campaign_id] = campaign
        session['last_campaign_id'] = campaign_id
        
        # Lancer la génération de la campagne en arrière-plan
        threading.Thread(target=generate_campaign_background, args=(campaign_id, artist, song, genres, language, promotion_type, lyrics, bio, song_link)).start()
        
        # Rediriger vers la page de statut de la campagne
        return redirect(url_for('campaign_status_page', id=campaign_id))
    
    # Si la méthode n'est pas POST, rediriger vers la page d'accueil
    return redirect(url_for('index'))

# Ajouter cette nouvelle route pour afficher la page de statut
@app.route('/campaign_status_page')
def campaign_status_page():
    campaign_id = request.args.get('id')
    if not campaign_id:
        flash("Aucun identifiant de campagne fourni.")
        return redirect(url_for('index'))
    
    return render_template('campaign_status.html', campaign_id=campaign_id)

# Ajouter cette nouvelle route pour afficher les résultats
@app.route('/campaign_results/<id>')
def view_campaign_results(id):
    # Récupérer les données de la campagne
    campaigns = session.get('campaigns', {})
    campaign = campaigns.get(id)
    
    if not campaign:
        flash("Campagne non trouvée.")
        return redirect(url_for('index'))
    
    # Vérifier si la campagne est terminée
    if campaign.get('status') != 'completed':
        # Si la campagne n'est pas terminée, rediriger vers la page de statut
        return redirect(url_for('campaign_status_page', id=id))
    
    # Rendre le template avec les données de la campagne
    return render_template('campaign_results.html', campaign=campaign)
