import html
import json
from pathlib import Path


WIDTH = 1080
HEIGHT = 1920


STYLE_CONFIG = {
    "dark": {"overlay": "rgba(0,0,0,0.58)", "text": "#ffffff", "accent": "#aaaaaa"},
    "soft": {"overlay": "rgba(20,20,20,0.30)", "text": "#ffffff", "accent": "#eeeeee"},
    "colourful": {"overlay": "rgba(30,10,60,0.30)", "text": "#ffffff", "accent": "#ffe082"},
    "cinematic": {"overlay": "rgba(0,0,0,0.45)", "text": "#ffffff", "accent": "#f5d58a"},
    "powerful": {"overlay": "rgba(0,0,0,0.52)", "text": "#ffffff", "accent": "#ffcc66"},
}


def build_canvas_html(
    quote: str,
    image_paths,
    style: str = "cinematic",
    fps: int = 30,
    duration_seconds: int = 10,
) -> str:

    style_key = style.lower().strip()
    if style_key not in STYLE_CONFIG:
        style_key = "cinematic"
    config = STYLE_CONFIG[style_key]

    safe_quote = html.escape(quote)

    if not image_paths:
        raise ValueError("At least one image_path is required.")

    absolute_image_uris = [Path(p).resolve().as_uri() for p in image_paths]

    style_json = json.dumps(config)
    image_uris_json = json.dumps(absolute_image_uris)

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    html, body {{
        width: {WIDTH}px;
        height: {HEIGHT}px;
        overflow: hidden;
        background: #000;
    }}
    canvas {{ display: block; width: {WIDTH}px; height: {HEIGHT}px; }}
</style>
</head>
<body>
<canvas id="canvas" width="{WIDTH}" height="{HEIGHT}"></canvas>
<script>

const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");

const WIDTH = {WIDTH};
const HEIGHT = {HEIGHT};
const DURATION = {duration_seconds};
const FPS = {fps};

const quote = {json.dumps(safe_quote)};
const imagePaths = {image_uris_json};
const style = {style_json};

// Each image gets its own load/failure state. A failed image just
// falls back to a dark background instead of hanging the whole
// render — same idea as the earlier single-image fix, now applied
// per-image since more images means more chances for one to fail.
const images = imagePaths.map(function(src) {{
    const state = {{ failed: false }};
    const img = new Image();
    img.onerror = function() {{ state.failed = true; }};
    img.src = src;
    state.img = img;
    return state;
}});

function clamp(value, min, max) {{
    return Math.max(min, Math.min(max, value));
}}

function easeInOut(t) {{
    return t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
}}

function wrapText(text, maxWidth) {{
    const words = text.split(" ");
    const lines = [];
    let line = "";
    for (const word of words) {{
        const testLine = line ? line + " " + word : word;
        if (ctx.measureText(testLine).width > maxWidth && line) {{
            lines.push(line);
            line = word;
        }} else {{
            line = testLine;
        }}
    }}
    if (line) {{ lines.push(line); }}
    return lines;
}}

// Idea: the timeline splits into one equal segment per image, with a
// short crossfade at each boundary — reads as an intentional
// multi-shot edit instead of a jarring hard cut between photos.
const CROSSFADE_SECONDS = Math.min(0.6, (DURATION / images.length) / 2);

function getActiveSegment(t) {{
    const segmentDuration = DURATION / images.length;
    let index = Math.floor(t / segmentDuration);
    index = clamp(index, 0, images.length - 1);
    const segmentStart = index * segmentDuration;
    return {{
        index: index,
        segmentDuration: segmentDuration,
        localT: t - segmentStart,
    }};
}}

function drawSingleImage(state, progress) {{
    if (state.failed || !state.img.complete || state.img.naturalWidth === 0) {{
        return false;
    }}
    const img = state.img;
    const scale = Math.max(WIDTH / img.naturalWidth, HEIGHT / img.naturalHeight);
    const imageWidth = img.naturalWidth * scale;
    const imageHeight = img.naturalHeight * scale;
    const maxX = Math.max(0, imageWidth - WIDTH);
    const maxY = Math.max(0, imageHeight - HEIGHT);
    const eased = easeInOut(clamp(progress, 0, 1));
    const zoom = 1.0 + (0.08 * eased);
    const drawWidth = imageWidth * zoom;
    const drawHeight = imageHeight * zoom;
    const x = -(maxX * eased);
    const y = -(maxY * eased * 0.35);
    ctx.drawImage(img, x, y, drawWidth, drawHeight);
    return true;
}}

function drawImages(t) {{
    const segment = getActiveSegment(t);
    const segProgress = segment.localT / segment.segmentDuration;

    const current = images[segment.index];
    const drewCurrent = drawSingleImage(current, segProgress);

    if (!drewCurrent) {{
        ctx.fillStyle = "#111111";
        ctx.fillRect(0, 0, WIDTH, HEIGHT);
    }}

    const timeLeftInSegment = segment.segmentDuration - segment.localT;

    if (segment.index < images.length - 1 && timeLeftInSegment < CROSSFADE_SECONDS) {{
        const next = images[segment.index + 1];
        const fadeIn = clamp(1 - (timeLeftInSegment / CROSSFADE_SECONDS), 0, 1);
        ctx.save();
        ctx.globalAlpha = fadeIn;
        drawSingleImage(next, 0);
        ctx.restore();
    }}
}}

function drawOverlay() {{
    const gradient = ctx.createLinearGradient(0, 0, 0, HEIGHT);
    gradient.addColorStop(0, "rgba(0,0,0,0.18)");
    gradient.addColorStop(0.45, style.overlay);
    gradient.addColorStop(1, "rgba(0,0,0,0.75)");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, WIDTH, HEIGHT);
}}

function drawQuote(t) {{
    const fadeDuration = Math.min(0.6, DURATION * 0.12);
    const start = fadeDuration + 0.2;
    const end = DURATION - (fadeDuration + 0.2);

    let opacity = 1;

    if (t < start) {{
        opacity = clamp((t - 0.2) / fadeDuration, 0, 1);
    }}
    if (t > end) {{
        opacity = clamp(1 - ((t - end) / fadeDuration), 0, 1);
    }}

    const localTime = clamp((t - start) / Math.max(0.4, fadeDuration * 1.5), 0, 1);
    const animation = easeInOut(localTime);
    const yOffset = 80 * (1 - animation);

    ctx.save();
    ctx.globalAlpha = opacity;
    ctx.font = "700 68px Arial, Helvetica, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    const maxWidth = 850;
    const lines = wrapText(quote, maxWidth);
    const lineHeight = 92;
    const totalHeight = lines.length * lineHeight;
    const centerY = HEIGHT / 2 - totalHeight / 2;

    ctx.shadowColor = "rgba(0,0,0,0.65)";
    ctx.shadowBlur = 25;
    ctx.shadowOffsetY = 8;
    ctx.fillStyle = style.text;

    lines.forEach((line, index) => {{
        ctx.fillText(line, WIDTH / 2, centerY + index * lineHeight + yOffset);
    }});

    ctx.restore();
}}

function drawBranding() {{
    ctx.save();
    ctx.globalAlpha = 0.82;
    ctx.font = "600 30px Arial, Helvetica, sans-serif";
    ctx.textAlign = "center";
    ctx.fillStyle = style.accent;
    ctx.fillText("J TEC VIDEO PRODUCTION", WIDTH / 2, HEIGHT - 100);
    ctx.restore();
}}

function drawVignette() {{
    const gradient = ctx.createRadialGradient(
        WIDTH / 2, HEIGHT / 2, HEIGHT * 0.2,
        WIDTH / 2, HEIGHT / 2, HEIGHT * 0.8
    );
    gradient.addColorStop(0, "rgba(0,0,0,0)");
    gradient.addColorStop(1, "rgba(0,0,0,0.65)");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, WIDTH, HEIGHT);
}}

window.renderCanvasFrame = function(t) {{
    ctx.clearRect(0, 0, WIDTH, HEIGHT);
    drawImages(t);
    drawOverlay();
    drawQuote(t);
    drawBranding();
    drawVignette();
}};

window.isCanvasReady = function() {{
    return images.every(function(state) {{
        return state.failed || (state.img.complete && state.img.naturalWidth > 0);
    }});
}};

</script>
</body>
</html>
"""


def save_canvas_html(
    output_path: str,
    quote: str,
    image_paths,
    style: str = "cinematic",
    fps: int = 30,
    duration_seconds: int = 10,
):
    html_content = build_canvas_html(
        quote=quote,
        image_paths=image_paths,
        style=style,
        fps=fps,
        duration_seconds=duration_seconds,
    )

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(html_content)

    return output_path
