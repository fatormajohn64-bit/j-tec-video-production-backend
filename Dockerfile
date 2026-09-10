FROM python:3.11-slim

WORKDIR /app

# FFmpeg for encoding, fonts-liberation for text rendering (Pillow
# needs an actual .ttf font file — Liberation Sans is metric-compatible
# with Arial, so it looks the same as before). No more Chromium/browser
# dependencies — Pillow draws frames directly, no headless browser needed.
RUN apt-get update && \
    apt-get install -y \
    ffmpeg \
    ca-certificates \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p generated assets/cache

EXPOSE 10000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]
