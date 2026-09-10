from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 1080
HEIGHT = 1920

FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"


STYLE_CONFIG = {
    "dark":      {"overlay": (0, 0, 0, 148),   "text": (255, 255, 255), "accent": (170, 170, 170)},
    "soft":      {"overlay": (20, 20, 20, 77), "text": (255, 255, 255), "accent": (238, 238, 238)},
    "colourful": {"overlay": (30, 10, 60, 77), "text": (255, 255, 255), "accent": (255, 224, 130)},
    "cinematic": {"overlay": (0, 0, 0, 115),   "text": (255, 255, 255), "accent": (245, 213, 138)},
    "powerful":  {"overlay": (0, 0, 0, 133),   "text": (255, 255, 255), "accent": (255, 204, 102)},
}


def clamp(value, low, high):
    return max(low, min(high, value))


def ease_in_out(t):
    return 2 * t * t if t < 0.5 else 1 - ((-2 * t + 2) ** 2) / 2


def resolve_style(style):
    key = style.lower().strip()
    return key if key in STYLE_CONFIG else "cinematic"


# Idea kept from the earlier fix: a bad/missing image no longer fails
# the whole job. Pillow raises immediately on a broken file (unlike
# the old async onerror check), so we catch it per-image here and
# fall back to a plain dark frame instead of crashing the render.
def prepare_images(image_paths):
    prepared = []
    for path in image_paths:
        try:
            img = Image.open(path).convert("RGB")
            scale = max(WIDTH / img.width, HEIGHT / img.height)
            new_w = max(WIDTH, int(img.width * scale) + 1)
            new_h = max(HEIGHT, int(img.height * scale) + 1)
            prepared.append(img.resize((new_w, new_h), Image.LANCZOS))
        except Exception:
            prepared.append(Image.new("RGB", (WIDTH, HEIGHT), (17, 17, 17)))
    return prepared


def build_overlay_gradient(style_key):
    config = STYLE_CONFIG[style_key]
    top = (0, 0, 0, 46)
    mid = config["overlay"]
    bottom = (0, 0, 0, 191)
    stops = [(0.0, top), (0.45, mid), (1.0, bottom)]

    gradient = Image.new("RGBA", (1, HEIGHT))
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        for i in range(len(stops) - 1):
            t0, c0 = stops[i]
            t1, c1 = stops[i + 1]
            if t0 <= t <= t1:
                local = 0 if t1 == t0 else (t - t0) / (t1 - t0)
                color = tuple(int(c0[ch] + (c1[ch] - c0[ch]) * local) for ch in range(4))
                gradient.putpixel((0, y), color)
                break

    return gradient.resize((WIDTH, HEIGHT))


def build_vignette():
    # Built at low resolution then scaled up — a radial gradient has no
    # fine detail to lose, and this avoids a 2-million-pixel Python loop.
    scale = 10
    sw, sh = WIDTH // scale, HEIGHT // scale
    vignette = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    cx, cy = WIDTH / 2, HEIGHT / 2
    inner = HEIGHT * 0.2
    outer = HEIGHT * 0.8
    max_alpha = 166

    pixels = vignette.load()
    for y in range(sh):
        for x in range(sw):
            dx = (x * scale) - cx
            dy = (y * scale) - cy
            dist = (dx * dx + dy * dy) ** 0.5
            if dist <= inner:
                a = 0
            elif dist >= outer:
                a = max_alpha
            else:
                a = int(max_alpha * (dist - inner) / (outer - inner))
            pixels[x, y] = (0, 0, 0, a)

    return vignette.resize((WIDTH, HEIGHT), Image.BILINEAR)


def build_branding_layer(style_key):
    config = STYLE_CONFIG[style_key]
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    font = ImageFont.truetype(FONT_BOLD, 30)

    text = "J TEC VIDEO PRODUCTION"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    x = (WIDTH - text_w) / 2
    y = HEIGHT - 100

    color = config["accent"] + (int(255 * 0.82),)
    draw.text((x, y), text, font=font, fill=color)
    return layer


def wrap_text(draw, text, font, max_width):
    words = text.split(" ")
    lines = []
    line = ""
    for word in words:
        test_line = f"{line} {word}".strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if (bbox[2] - bbox[0]) > max_width and line:
            lines.append(line)
            line = word
        else:
            line = test_line
    if line:
        lines.append(line)
    return lines


def draw_quote_layer(quote, style_key, t, duration):
    config = STYLE_CONFIG[style_key]
    layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    font = ImageFont.truetype(FONT_BOLD, 68)

    fade_duration = min(0.6, duration * 0.12)
    start = fade_duration + 0.2
    end = duration - (fade_duration + 0.2)

    opacity = 1.0
    if t < start:
        opacity = clamp((t - 0.2) / fade_duration, 0, 1)
    if t > end:
        opacity = clamp(1 - ((t - end) / fade_duration), 0, 1)

    local_time = clamp((t - start) / max(0.4, fade_duration * 1.5), 0, 1)
    animation = ease_in_out(local_time)
    y_offset = 80 * (1 - animation)

    max_width = 850
    lines = wrap_text(draw, quote, font, max_width)
    line_height = 92
    total_height = len(lines) * line_height
    center_y = HEIGHT / 2 - total_height / 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (WIDTH - text_w) / 2
        y = center_y + i * line_height + y_offset

        # Simple offset shadow (no blur) — a lighter-weight stand-in
        # for the canvas version's shadowBlur, kept fast per-frame.
        draw.text((x + 3, y + 6), line, font=font, fill=(0, 0, 0, int(160 * opacity)))
        draw.text((x, y), line, font=font, fill=config["text"] + (int(255 * opacity),))

    return layer


def get_active_segment(t, duration, num_images):
    segment_duration = duration / num_images
    index = clamp(int(t // segment_duration), 0, num_images - 1)
    local_t = t - (index * segment_duration)
    return index, segment_duration, local_t


def draw_single_image(prepared_img, progress):
    eased = ease_in_out(clamp(progress, 0, 1))
    zoom = 1.0 + (0.08 * eased)
    draw_w = int(prepared_img.width * zoom)
    draw_h = int(prepared_img.height * zoom)
    resized = prepared_img.resize((draw_w, draw_h), Image.BILINEAR)

    max_x = max(0, draw_w - WIDTH)
    max_y = max(0, draw_h - HEIGHT)
    x = int(max_x * eased)
    y = int(max_y * eased * 0.35)

    return resized.crop((x, y, x + WIDTH, y + HEIGHT))


def draw_background(t, prepared_images, duration):
    num_images = len(prepared_images)
    index, seg_dur, local_t = get_active_segment(t, duration, num_images)
    progress = local_t / seg_dur if seg_dur > 0 else 0

    current = draw_single_image(prepared_images[index], progress)

    crossfade_seconds = min(0.6, seg_dur / 2) if seg_dur > 0 else 0
    time_left = seg_dur - local_t

    if index < num_images - 1 and crossfade_seconds > 0 and time_left < crossfade_seconds:
        next_img = draw_single_image(prepared_images[index + 1], 0)
        fade_in = clamp(1 - (time_left / crossfade_seconds), 0, 1)
        current = Image.blend(current, next_img, fade_in)

    return current


def render_frame(
    t,
    duration,
    prepared_images,
    quote,
    style_key,
    overlay_layer,
    vignette_layer,
    branding_layer,
):
    frame = draw_background(t, prepared_images, duration).convert("RGBA")
    frame.alpha_composite(overlay_layer)
    frame.alpha_composite(draw_quote_layer(quote, style_key, t, duration))
    frame.alpha_composite(branding_layer)
    frame.alpha_composite(vignette_layer)
    return frame.convert("RGB")
