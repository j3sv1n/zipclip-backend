FROM python:3.10-slim

# Install system dependencies for FFmpeg and ImageMagick
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libavdevice-dev \
    libavfilter-dev \
    libopus-dev \
    libvpx-dev \
    pkg-config \
    libsrtp2-dev \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

# Fix ImageMagick policy for MoviePy text/subtitles
RUN sed -i 's/rights="none" pattern="@\*"/rights="read|write" pattern="@*"/' /etc/ImageMagick-6/policy.xml || true

# Create a non-root user required by Hugging Face Spaces
RUN useradd -m -u 1000 user

WORKDIR /app

# Install Python requirements
COPY zipclip-backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend and frontend folders and set permissions
COPY --chown=user:user zipclip-backend/ /app/zipclip-backend/
COPY --chown=user:user zipclip-web/ /app/zipclip-web/

USER user
WORKDIR /app/zipclip-backend
CMD ["python", "api.py"]