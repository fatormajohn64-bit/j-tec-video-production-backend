import io
import subprocess
from pathlib import Path

from app.services.canvas_renderer import (
    prepare_images,
    build_overlay_gradient,
    build_vignette,
    build_branding_layer,
    render_frame,
    resolve_style,
)


def render_video(
    quote: str,
    image_paths,
    style: str,
    output_path: str,
    fps: int = 30,
    duration_seconds: int = 10,
):
    total_frames = fps * duration_seconds

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    style_key = resolve_style(style)

    # These three layers don't change frame to frame — building them
    # once up front instead of per-frame is most of why this is fast.
    prepared_images = prepare_images(image_paths)
    overlay_layer = build_overlay_gradient(style_key)
    vignette_layer = build_vignette()
    branding_layer = build_branding_layer(style_key)

    ffmpeg_command = [
        "ffmpeg", "-y",
        "-f", "image2pipe",
        "-vcodec", "png",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-an",
        str(output_file),
    ]

    process = subprocess.Popen(
        ffmpeg_command,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    try:
        for frame_number in range(total_frames):
            t = frame_number / fps

            frame = render_frame(
                t=t,
                duration=duration_seconds,
                prepared_images=prepared_images,
                quote=quote,
                style_key=style_key,
                overlay_layer=overlay_layer,
                vignette_layer=vignette_layer,
                branding_layer=branding_layer,
            )

            buffer = io.BytesIO()
            frame.save(buffer, format="PNG")
            process.stdin.write(buffer.getvalue())

        process.stdin.close()
        return_code = process.wait()

        if return_code != 0:
            error = process.stderr.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"FFmpeg failed:\\n{error}")

    except Exception:
        try:
            process.stdin.close()
        except Exception:
            pass
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        raise

    if not output_file.exists():
        raise RuntimeError("Video rendering completed but MP4 was not created.")

    return str(output_file)
