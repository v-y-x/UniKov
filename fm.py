import requests
import os
from dotenv import load_dotenv

load_dotenv()

LASTFM_API_KEY = os.getenv('LASTFM_API')

def get_track_info(artist, track):
    url = "https://ws.audioscrobbler.com/2.0/"
    params = {
        "method": "track.getInfo",
        "api_key": LASTFM_API_KEY,
        "artist": artist,
        "track": track,
        "format": "json",
    }
    response = requests.get(url, params=params)
    data = response.json()

    if "error" in data:
        return None

    return data["track"]