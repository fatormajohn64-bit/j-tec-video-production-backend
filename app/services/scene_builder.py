STYLE_SETTINGS = {
    "dark": {
        "mood": "dark and mysterious",
        "lighting": "low-key dramatic lighting",
    },
    "soft": {
        "mood": "peaceful and emotional",
        "lighting": "soft natural light",
    },
    "colourful": {
        "mood": "bright, energetic and joyful",
        "lighting": "vibrant cinematic lighting",
    },
    "cinematic": {
        "mood": "epic and inspiring",
        "lighting": "dramatic cinematic lighting",
    },
    "powerful": {
        "mood": "strong, intense and motivational",
        "lighting": "high-contrast dramatic lighting",
    },
}


KEYWORD_GROUPS = {
    "success": ["success", "winning", "achievement", "goal", "dream"],
    "strength": ["strength", "strong", "fight", "fighter", "power"],
    "journey": ["journey", "path", "road", "walk", "future"],
    "hope": ["hope", "believe", "faith", "tomorrow", "light"],
    "failure": ["failure", "fail", "mistake", "fall", "fallen"],
    "motivation": ["never give up", "keep going", "continue", "hard work", "discipline"],
}


# Idea: each keyword now maps to several candidate scenes instead of
# one. A single-image video still just uses the first match (same
# behavior as before), but a multi-image video can pull several
# distinct shots for the same theme instead of repeating one image
# description num_images times.
SCENE_LIBRARY = {
    "success": [
        "A determined person standing on a mountain overlooking a beautiful sunrise",
        "Someone raising their arms in victory at a mountain summit",
        "A person celebrating success on a hill overlooking a city skyline",
        "Silhouette of a person reaching the peak of a mountain at golden hour",
    ],
    "strength": [
        "A powerful person walking through dramatic mountains under storm clouds",
        "A lone figure standing firm against strong winds on a rugged cliff",
        "A person training hard, silhouetted against a dramatic sunset",
        "A strong figure climbing a steep rocky trail",
    ],
    "journey": [
        "A lone person walking along a long road toward golden sunlight",
        "A winding road stretching toward distant mountains at dawn",
        "A person walking through a foggy forest path toward the light",
        "Footprints on a long road leading toward the horizon",
    ],
    "hope": [
        "A peaceful landscape with sunlight breaking through dark clouds",
        "Sunrise breaking over calm ocean waves",
        "A single light glowing in a quiet, misty landscape",
        "Golden light spilling over a quiet valley at dawn",
    ],
    "failure": [
        "A person rising after falling, standing firmly against a dramatic landscape",
        "A figure standing back up after being knocked down, dramatic lighting",
        "A person dusting themselves off as a stormy sky clears",
        "A determined figure getting back on their feet on a rocky path",
    ],
    "motivation": [
        "A cinematic person looking toward a beautiful sunrise, symbolizing a new beginning",
        "A person running toward the horizon at sunrise, full of energy",
        "Someone looking out over a vast landscape, full of determination",
        "A person standing tall against a dramatic sky, ready to take action",
    ],
}


def extract_keywords(quote: str):
    text = quote.lower()
    found = []

    for category, words in KEYWORD_GROUPS.items():
        for word in words:
            if word in text:
                found.append(category)
                break

    if not found:
        found = ["motivation"]

    return list(dict.fromkeys(found))


def choose_scenes(keywords, num_images):
    pool = []

    for keyword in keywords:
        pool.extend(SCENE_LIBRARY.get(keyword, []))

    if not pool:
        pool = SCENE_LIBRARY["motivation"]

    pool = list(dict.fromkeys(pool))

    scenes = []
    index = 0

    while len(scenes) < num_images:
        scenes.append(pool[index % len(pool)])
        index += 1

    return scenes


def build_scene(
    quote: str,
    style: str,
    num_images: int = 1,
    fps: int = 30,
    duration_seconds: int = 10,
):
    style_key = style.lower().strip()

    if style_key not in STYLE_SETTINGS:
        style_key = "cinematic"

    settings = STYLE_SETTINGS[style_key]
    keywords = extract_keywords(quote)
    scenes = choose_scenes(keywords, num_images)

    return {
        "visual_keywords": keywords,
        "scene_descriptions": scenes,
        "mood": settings["mood"],
        "lighting": settings["lighting"],
        "camera": "slow cinematic push-in",
        "aspect_ratio": "9:16",
        "duration_seconds": duration_seconds,
        "fps": fps,
        "num_images": num_images,
        "resolution": "1080x1920",
}
