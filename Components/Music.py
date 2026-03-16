import os
import random
from Components.YoutubeDownloader import download_youtube_video

# Pre-defined high-quality royalty-free music library (fallback)
MUSIC_LIBRARY = {
    "upbeat": [
        "https://www.youtube.com/watch?v=kGgJbeT9pM8", # Numall Fix - Avowal
    ],
    "calm": [
        "https://www.youtube.com/watch?v=S7b8ADhadpE", # Onycs - Dreamcatcher
    ],
    "lofi": [
        "https://www.youtube.com/watch?v=9hf9T8D8B6M", # Lakey Inspired - Blue Boi
    ],
    "energetic": [
        "https://www.youtube.com/watch?v=kGgJbeT9pM8",
    ],
    "inspiring": [
        "https://www.youtube.com/watch?v=S7b8ADhadpE",
    ]
}

# Aligned path: Components/assets/music
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_DIR = os.path.join(BASE_DIR, "assets", "music")
os.makedirs(MUSIC_DIR, exist_ok=True)

def select_and_download_music(mood_suggestion):
    """
    Selects a music track. Prioritizes local files in MUSIC_DIR. 
    Fallbacks to downloading from Youtube if no suitable local file is found.
    """
    mood_suggestion = mood_suggestion.lower()
    
    # Simple matching to determine key
    selected_mood = "lofi" # Default
    for mood in MUSIC_LIBRARY.keys():
        if mood in mood_suggestion:
            selected_mood = mood
            break

    # 1. 🔍 Check for local music first
    local_files = []
    if os.path.exists(MUSIC_DIR):
        for f in os.listdir(MUSIC_DIR):
            if f.lower().endswith(('.mp3', '.wav', '.m4a', '.mp4')):
                # If the filename contains the mood keyword, prioritize it
                if selected_mood in f.lower():
                    print(f"  Found local music matching mood '{selected_mood}': {f}")
                    return os.path.join(MUSIC_DIR, f)
                local_files.append(os.path.join(MUSIC_DIR, f))

    # 2. If no direct match, but some local files exist, maybe use them?
    if local_files and random.random() < 0.7:
        selected = random.choice(local_files)
        print(f"  Using random local music: {os.path.basename(selected)}")
        return selected

    # 3. 🌐 Fallback to YouTube
    track_url = random.choice(MUSIC_LIBRARY[selected_mood])
    print(f"  No suitable local music. Downloading {selected_mood} from: {track_url}")
    
    music_file = download_youtube_video(track_url)
    
    if music_file and os.path.exists(music_file):
        # Move to music assets directory for future use
        target_path = os.path.join(MUSIC_DIR, f"{selected_mood}_{os.path.basename(music_file)}")
        os.rename(music_file, target_path)
        return target_path
        
    return None
