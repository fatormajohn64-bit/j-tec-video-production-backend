import html
import json
from pathlib import Path


WIDTH = 1080
HEIGHT = 1920
FPS = 60
DURATION = 10


STYLE_CONFIG = {
    "dark": {
        "overlay": "rgba(0,0,0,0.58)",
        "text": "#ffffff",
        "accent": "#aaaaaa",
    },
    "soft": {
        "overlay": "rgba(20,20,20,0.30)",
        "text": "#ffffff",
        "accent": "#eeeeee",
    },
    "colourful": {
        "overlay": "rgba(30,10,60,0.30)",
        "text": "#ffffff",
        "accent": "#ffe082",
    },
    "cinematic": {
        "overlay": "rgba(0,0,0,0.45)",
        "text": "#ffffff",
        "accent": "#f5d58a",
    },
    "powerful": {
        "overlay": "rgba(0,0,0,0.52)",
        "text": "#ffffff",
        "accent": "#ffcc66",
    },
}


def build_canvas_html(
    quote: str,
    image_path: str,
    style: str = "cinematic",
) -> str:

    style_key = style.lower().strip()

    if style_key not in STYLE_CONFIG:
        style_key = "cinematic"

    config = STYLE_CONFIG[style_key]

    safe_quote = html.escape(quote)

    # BUG FIX: image_path was relative (e.g. "assets/cache/xxx.jpg").
    # "file://" + a relative path is not a valid file URL — Chromium
    # parses everything after "file://" as a hostname, so the image
    # silently failed to load and isCanvasReady() never returned true,
    # which is why rendering hung until the 30s Playwright timeout.
    # Path(...).resolve().as_uri() builds a correct absolute file:// URI.
    absolute_image_uri = Path(image_path).resolve().as_uri()

    style_json = json.dumps(config)

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">

<style>
    * {{
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }}

    html, body {{
        width: {WIDTH}px;
        height: {HEIGHT}px;
        overflow: hidden;
        background: #000;
    }}

    canvas {{
        display: block;
        width: {WIDTH}px;
        height: {HEIGHT}px;
    }}
</style>
</head>

<body>

<canvas id="canvas"
        width="{WIDTH}"
        height="{HEIGHT}">
</canvas>

<script>

const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");

const WIDTH = {WIDTH};
const HEIGHT = {HEIGHT};

const quote = {json.dumps(safe_quote)};
const imagePath = {json.dumps(absolute_image_uri)};

const style = {style_json};

const image = new Image();

// Idea: don't let a bad/missing image hang the whole render forever.
// If the image fails to load for any reason, flip this flag so
// isCanvasReady() still resolves and drawImage() falls back to a
// plain dark background instead of timing out the entire job.
let imageFailed = false;
image.onerror = function() {{
    imageFailed = true;
}};

image.src = imagePath;

function clamp(value, min, max) {{
    return Math.max(min, Math.min(max, value));
}}

function easeInOut(t) {{
    return t < 0.5
        ? 2 * t * t
        : 1 - Math.pow(-2 * t + 2, 2) / 2;
}}

function wrapText(text, maxWidth) {{

    const words = text.split(" ");
    const lines = [];

    let line = "";

    for (const word of words) {{

        const testLine = line
            ? line + " " + word
            : word;

        if (ctx.measureText(testLine).width > maxWidth && line) {{
            lines.push(line);
            line = word;
        }} else {{
            line = testLine;
        }}
    }}

    if (line) {{
        lines.push(line);
    }}

    return lines;
}}

function drawImage(t) {{

    if (imageFailed || !image.complete || image.naturalWidth === 0) {{
        ctx.fillStyle = "#111111";
        ctx.fillRect(0, 0, WIDTH, HEIGHT);
        return;
    }}

    const scale = Math.max(
        WIDTH / image.naturalWidth,
        HEIGHT / image.naturalHeight
    );

    const imageWidth = image.naturalWidth * scale;
    const imageHeight = image.naturalHeight * scale;

    const maxX = Math.max(0, imageWidth - WIDTH);
    const maxY = Math.max(0, imageHeight - HEIGHT);

    const progress = easeInOut(t / {DURATION});

    const zoom = 1.0 + (0.08 * progress);

    const drawWidth = imageWidth * zoom;
    const drawHeight = imageHeight * zoom;

    const x = -(maxX * progress);
    const y = -(maxY * progress * 0.35);

    ctx.drawImage(
        image,
        x,
        y,
        drawWidth,
        drawHeight
    );
}}

function drawOverlay() {{

    const gradient = ctx.createLinearGradient(
        0,
        0,
        0,
        HEIGHT
    );

    gradient.addColorStop(
        0,
        "rgba(0,0,0,0.18)"
    );

    gradient.addColorStop(
        0.45,
        style.overlay
    );

    gradient.addColorStop(
        1,
        "rgba(0,0,0,0.75)"
    );

    ctx.fillStyle = gradient;

    ctx.fillRect(
        0,
        0,
        WIDTH,
        HEIGHT
    );
}}

function drawQuote(t) {{

    const start = 1.0;
    const end = 8.8;

    let opacity = 1;

    if (t < start) {{
        opacity = clamp(
            (t - 0.3) / 0.7,
            0,
            1
        );
    }}

    if (t > end) {{
        opacity = clamp(
            1 - ((t - end) / 0.8),
            0,
            1
        );
    }}

    const localTime = clamp(
        (t - start) / 1.2,
        0,
        1
    );

    const animation = easeInOut(localTime);

    const yOffset = 80 * (1 - animation);

    ctx.save();

    ctx.globalAlpha = opacity;

    ctx.font =
        "700 68px Arial, Helvetica, sans-serif";

    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    const maxWidth = 850;

    const lines = wrapText(
        quote,
        maxWidth
    );

    const lineHeight = 92;

    const totalHeight =
        lines.length * lineHeight;

    const centerY =
        HEIGHT / 2 - totalHeight / 2;

    ctx.shadowColor =
        "rgba(0,0,0,0.65)";

    ctx.shadowBlur = 25;
    ctx.shadowOffsetY = 8;

    ctx.fillStyle = style.text;

    lines.forEach((line, index) => {{

        ctx.fillText(
            line,
            WIDTH / 2,
            centerY +
            index * lineHeight +
            yOffset
        );

    }});

    ctx.restore();
}}

function drawBranding() {{

    ctx.save();

    ctx.globalAlpha = 0.82;

    ctx.font =
        "600 30px Arial, Helvetica, sans-serif";

    ctx.textAlign = "center";

    ctx.fillStyle = style.accent;

    ctx.fillText(
        "J TEC VIDEO PRODUCTION",
        WIDTH / 2,
        HEIGHT - 100
    );

    ctx.restore();
}}

function drawVignette() {{

    const gradient =
        ctx.createRadialGradient(
            WIDTH / 2,
            HEIGHT / 2,
            HEIGHT * 0.2,
            WIDTH / 2,
            HEIGHT / 2,
            HEIGHT * 0.8
        );

    gradient.addColorStop(
        0,
        "rgba(0,0,0,0)"
    );

    gradient.addColorStop(
        1,
        "rgba(0,0,0,0.65)"
    );

    ctx.fillStyle = gradient;

    ctx.fillRect(
        0,
        0,
        WIDTH,
        HEIGHT
    );
}}

window.renderCanvasFrame = function(t) {{

    ctx.clearRect(
        0,
        0,
        WIDTH,
        HEIGHT
    );

    drawImage(t);

    drawOverlay();

    drawQuote(t);

    drawBranding();

    drawVignette();
}};

window.isCanvasReady = function() {{
    return imageFailed ||
           (image.complete && image.naturalWidth > 0);
}};

</script>

</body>
</html>
"""


def save_canvas_html(
    output_path: str,
    quote: str,
    image_path: str,
    style: str = "cinematic",
):

    html_content = build_canvas_html(
        quote=quote,
        image_path=image_path,
        style=style,
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as file:
        file.write(html_content)

    return output_path
