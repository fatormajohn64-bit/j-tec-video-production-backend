import os
import hashlib
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

CACHE_DIR = Path("assets/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def create_image_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def search_pexels(query: str, per_page: int = 10):
    if not PEXELS_API_KEY:
        raise RuntimeError(
            "PEXELS_API_KEY is missing. Add it to your Render environment variables."
        )

    response = httpx.get(
        "https://api.pexels.com/v1/search",
        headers={
            "Authorization": PEXELS_API_KEY,
        },
        params={
            "query": query,
            "orientation": "portrait",
            "size": "large",
            "per_page": per_page,
        },
        timeout=20,
    )

    response.raise_for_status()

    return response.json().get("photos", [])


def download_image(url: str, image_id: str) -> str:
    extension = ".jpg"
    output_path = CACHE_DIR / f"{image_id}{extension}"

    if output_path.exists():
        return str(output_path)

    response = httpx.get(
        url,
        timeout=30,
        follow_redirects=True,
    )

    response.raise_for_status()

    output_path.write_bytes(response.content)

    return str(output_path)


def find_matching_image(scene_description: str):
    photos = search_pexels(scene_description)

    if not photos:
        raise RuntimeError(
            "No matching image was found."
        )

    photo = photos[0]

    image_id = create_image_id(photo["id"].__str__())

    image_url = photo["src"]["large2x"]

    local_path = download_image(
        image_url,
        image_id,
    )

    return {
        "image_id": image_id,
        "image_url": image_url,
        "local_path": local_path,
        "photographer": photo.get("photographer"),
        "source": "pexels",
    }
