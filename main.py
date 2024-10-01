import os
import numpy as np
from flask import Flask, render_template, request, redirect, url_for
from google.cloud import vision
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/ameliado/web102/image-to-playlist/visonanalysis.json"

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

SPOTIPY_CLIENT_ID = "8759c04c79a24df5be56e6cf1bc390c5"
SPOTIPY_CLIENT_SECRET = "b5b6d509be424b18802d865b48b6dfb2"
auth_manager = SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET)
sp = spotipy.Spotify(auth_manager=auth_manager)

color_emotion_map = {
    (0, 0, 0): "Sadness",       # Black
    (84, 83, 85): "Neutral",    # Dark gray
    (121, 116, 110): "Neutral",  # Light gray/brown
    (55, 55, 56): "Sadness",     # Dark gray
    (156, 148, 141): "Neutral",  # Light gray/brown
    (195, 187, 180): "Comfort",  # Light beige
    (26, 26, 26): "Sadness",     # Black
    (41, 55, 69): "Calmness",    # Dark blue-gray
    (66, 76, 90): "Seriousness",  # Dark gray-blue
    (243, 235, 227): "Comfort",   # Light beige
    (63, 53, 41): "Sadness",      # Dark brown
    (117, 77, 93): "Romantic",    # Dark pink
    (115, 122, 208): "Calmness",  # Light blue
    (180, 99, 98): "Anger",       # Red tone
    (121, 163, 226): "Joy",       # Light blue
    (176, 189, 228): "Joy",       # Light blue
    (147, 102, 114): "Romantic",  # Pink
    (125, 105, 193): "Joyful",    # Blue-purple
    (167, 97, 114): "Anger",      # Dark pink
    (209, 129, 123): "Sadness",   # Light red
    (103, 70, 101): "Sadness",    # Dark purple
    (199, 140, 126): "Warmth",    # Light brown
    (82, 84, 89): "Neutral",       # Dark gray
    (227, 134, 99): "Warmth",      # Light orange
    (242, 182, 131): "Happiness",   # Light orange
    (254, 230, 172): "Happiness",   # Light beige
    (162, 107, 95): "Warmth",      # Brown
    (116, 115, 119): "Neutral",    # Dark gray
    (51, 55, 60): "Seriousness",   # Dark gray
    (180, 89, 61): "Anger",        # Red
}

def get_emotion_from_rgba(r, g, b):
    closest_emotion = "Neutral"
    min_distance = float('inf')
    for color in color_emotion_map:
        distance = np.sqrt((r - color[0])**2 + (g - color[1])**2 + (b - color[2])**2)
        if distance < min_distance:
            min_distance = distance
            closest_emotion = color_emotion_map[color]
    return closest_emotion

def detect_properties(path):
    client = vision.ImageAnnotatorClient()
    with open(path, "rb") as image_file:
        content = image_file.read()
    image = vision.Image(content=content)
    response = client.image_properties(image=image)
    emotions_in_image = []

    if response.image_properties_annotation:
        for color in response.image_properties_annotation.dominant_colors.colors:
            r, g, b = color.color.red, color.color.green, color.color.blue
            emotion = get_emotion_from_rgba(r, g, b)
            emotions_in_image.append(emotion)
    
    return emotions_in_image

def search_playlist(emotions):
    flattened_emotions = [emotion for sublist in emotions for emotion in sublist]
    unique_emotions = set(flattened_emotions)
    search_query = " ".join(unique_emotions)

    playlists = []
    offset = 0
    limit = 5
    total_playlists_needed = 5

    while len(playlists) < total_playlists_needed:
        results = sp.search(q=search_query, type="playlist", limit=limit, offset=offset)

        if results['playlists']['items']:
            for item in results['playlists']['items']:
                owner_name = item['owner']['display_name'].lower()
                if owner_name != "spotify" and "official" not in owner_name:
                    playlist_info = {
                        'name': item['name'],
                        'url': item['external_urls']['spotify'],
                        'description': item['description'],
                        'owner': item['owner']['display_name'],
                        'id': item['id']
                    }
                    playlists.append(playlist_info)

            offset += limit
        else:
            break

    return playlists[:total_playlists_needed]


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        if "image" not in request.files:
            return redirect(request.url)
        file = request.files["image"]
        if file.filename == "":
            return redirect(request.url)
        if file:
            filepath = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(filepath)
            emotions = detect_properties(filepath)            
            playlists = search_playlist(emotions)
            
            return render_template("result.html", playlists=playlists)
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)