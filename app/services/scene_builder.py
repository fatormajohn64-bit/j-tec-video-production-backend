import re


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
    "success": [
        "success",
        "winning",
        "achievement",
        "goal",
        "dream",
    ],
    "strength": [
        "strength",
        "strong",
        "fight",
        "fighter",
        "power",
    ],
    "journey": [
        "journey",
        "path",
        "road",
        "walk",
        "future",
    ],
    "hope": [
        "hope",
        "believe",
        "faith",
        "tomorrow",
        "light",
    ],
    "failure": [
        "failure",
        "fail",
        "mistake",
        "fall",
        "fallen",
    ],
    "motivation": [
        "never give up",
        "keep going",
        "continue",
        "hard work",
        "discipline",
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


def choose_scene(keywords):
    if "success" in keywords:
        return "A determined person standing on a mountain overlooking a beautiful sunrise"

    if "strength" in keywords:
        return "A powerful person walking through dramatic mountains under storm clouds"

    if "journey" in keywords:
        return "A lone person walking along a long road toward golden sunlight"

    if "hope" in keywords:
        return "A peaceful landscape with sunlight breaking through dark clouds"

    if "failure" in keywords:
        return "A person rising after falling, standing firmly against a dramatic landscape"

    return "A cinematic person looking toward a beautiful sunrise, symbolizing a new beginning"


def build_scene(quote: str, style: str):
    style_key = style.lower().strip()

    if style_key not in STYLE_SETTINGS:
        style_key = "cinematic"

    settings = STYLE_SETTINGS[style_key]
    keywords = extract_keywords(quote)
    scene = choose_scene(keywords)

    return {
        "visual_keywords": keywords,
        "scene_description": scene,
        "mood": settings["mood"],
        "lighting": settings["lighting"],
        "camera": "slow cinematic push-in",
        "aspect_ratio": "9:16",
        "duration_seconds": 10,
        "fps": 60,
        "resolution": "1080x1920",
  }
