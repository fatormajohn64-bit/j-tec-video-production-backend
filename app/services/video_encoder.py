import os
import subprocess
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

from app.services.canvas_renderer import save_canvas_html


WIDTH = 1080
HEIGHT = 1920
FPS = 60
DURATION = 10
TOTAL_FRAMES = FPS * DURATION


def render_video(
    quote: str,
    image_path: str,
    style: str,
    output_path: str,
):
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:

        html_path = Path(temp_dir) / "scene.html"

        save_canvas_html(
            output_path=str(html_path),
            quote=quote,
            image_path=image_path,
            style=style,
        )

        ffmpeg_command = [
            "ffmpeg",
            "-y",

            # PNG frames arrive through stdin.
            "-f",
            "image2pipe",

            "-vcodec",
            "png",

            "-r",
            str(FPS),

            "-i",
            "-",

            "-c:v",
            "libx264",

            "-preset",
            "veryfast",

            "-crf",
            "20",

            "-pix_fmt",
            "yuv420p",

            "-movflags",
            "+faststart",

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
            with sync_playwright() as playwright:

                browser = playwright.chromium.launch(
                    headless=True
                )

                page = browser.new_page(
                    viewport={
                        "width": WIDTH,
                        "height": HEIGHT,
                    },
                    device_scale_factor=1,
                )

                page.goto(
                    html_path.as_uri(),
                    wait_until="load",
                )

                page.wait_for_function(
                    "window.isCanvasReady()"
                )

                for frame_number in range(TOTAL_FRAMES):

                    time_seconds = (
                        frame_number / FPS
                    )

                    page.evaluate(
                        """
                        (time) => {
                            window.renderCanvasFrame(time);
                        }
                        """,
                        time_seconds,
                    )

                    png_bytes = page.locator(
                        "#canvas"
                    ).screenshot(
                        type="png"
                    )

                    process.stdin.write(
                        png_bytes
                    )

                browser.close()

            process.stdin.close()

            return_code = process.wait()

            if return_code != 0:
                error = process.stderr.read().decode(
                    "utf-8",
                    errors="replace",
                )

                raise RuntimeError(
                    f"FFmpeg failed:\\n{error}"
                )

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
        raise RuntimeError(
            "Video rendering completed but MP4 was not created."
        )

    return str(output_file)
