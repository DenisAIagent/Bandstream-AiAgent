import os
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import logging
import openai
from pytrends.request import TrendReq
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pd.set_option('future.no_silent_downcasting', True)

load_dotenv()

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    logger.error("OPENAI_API_KEY is not set in environment variables")
    raise ValueError("OPENAI_API_KEY is required")

youtube_api_key = os.getenv("YOUTUBE_API_KEY")
if not youtube_api_key:
    logger.error("YOUTUBE_API_KEY is not set in environment variables")
    raise ValueError("YOUTUBE_API_KEY is required")
youtube = build("youtube", "v3", developerKey=youtube_api_key, cache_discovery=False)

pytrends = TrendReq(hl='fr', tz=360)

def get_google_trends(artist, song, genres):
    try:
        keywords = [artist, song] + genres[:2]  # Inclut la chanson
        pytrends.build_payload(keywords, cat=0, timeframe='today 3-m', geo='')
        interest_over_time = pytrends.interest_over_time()
        if not interest_over_time.empty:
            top_keyword = interest_over_time.sum().idxmax()
            return f"Trending interest in {top_keyword}"
        return "No significant trends found"
    except Exception as e:
        logger.error(f"Error fetching Google Trends: {str(e)}")
        return "No significant trends found"

def get_youtube_stats(artist, song):
    try:
        search_response = youtube.search().list(
            q=f"{artist} {song}",  # Recherche avec la chanson
            part="id,snippet",
            type="video",
            maxResults=5
        ).execute()
        
        total_views = 0
        video_count = 0
        for item in search_response.get("items", []):
            video_id = item["id"]["videoId"]
            video_response = youtube.videos().list(
                part="statistics",
                id=video_id
            ).execute()
            stats = video_response["items"][0]["statistics"]
            total_views += int(stats.get("viewCount", 0))
            video_count += 1
        
        avg_views = total_views / video_count if video_count > 0 else 0
        return avg_views > 10000
    except HttpError as e:
        logger.error(f"Error fetching YouTube stats: {str(e)}")
        return False

@app.route('/optimize', methods=['POST'])
def optimize():
    try:
        data = request.get_json()
        if not data or "artist" not in data or "song" not in data:
            logger.error("Missing required field 'artist' or 'song' in request")
            return jsonify({"error": "Missing required field 'artist' or 'song'"}), 400

        artist = data.get("artist")
        song = data.get("song")  # Nouveau champ
        genres = data.get("genres", ["metal"])
        logger.info(f"Optimizing campaign strategy for artist: {artist}, song: {song}")

        trend = get_google_trends(artist, song, genres)
        target_audience = f"Fans of {trend.split('in ')[-1]} and similar artists"

        youtube_popular = get_youtube_stats(artist, song)

        channels = ["Spotify", "YouTube"]
        if youtube_popular:
            budget_allocation = {"Spotify": 0.4, "YouTube": 0.6}
        else:
            budget_allocation = {"Spotify": 0.6, "YouTube": 0.4}

        prompt = f"""
        You are a marketing strategist specializing in music promotion. Optimize a campaign strategy for '{artist}' and their song '{song}' based on:
        - Trend: {trend}
        - YouTube popularity: {youtube_popular}

        Provide:
        - Target audience (short, based on trend and song)
        - Channels: Spotify, YouTube
        - Budget allocation (percentages totaling 1.0)

        Return JSON:
        {{
            "strategy": {{
                "target_audience": "<audience>",
                "channels": ["Spotify", "YouTube"],
                "budget_allocation": {{"Spotify": <float>, "YouTube": <float>}}
            }}
        }}
        """

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7
        )

        raw_text = response.choices[0].message.content.strip()
        logger.info(f"Raw response from OpenAI: {raw_text}")

        try:
            data = json.loads(raw_text)
            strategy = data.get("strategy", {
                "target_audience": target_audience,
                "channels": channels,
                "budget_allocation": budget_allocation
            })
        except json.JSONDecodeError:
            logger.warning("Failed to parse OpenAI response, using default strategy")
            strategy = {
                "target_audience": target_audience,
                "channels": channels,
                "budget_allocation": budget_allocation
            }

        return jsonify({"strategy": strategy}), 200

    except Exception as e:
        logger.error(f"Error optimizing campaign: {str(e)}")
        return jsonify({"error": "Failed to optimize campaign", "details": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Campaign Optimizer is running"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
