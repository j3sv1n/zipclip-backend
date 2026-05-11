FROM python:3.10-slim

# Install system dependencies for FFmpeg and ImageMagick
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    ffmpeg \
    libavdevice-dev \
    libavfilter-dev \
    libopus-dev \
    libvpx-dev \
    pkg-config \
    libsrtp2-dev \
    imagemagick \
    fontconfig \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Fix ImageMagick policy for MoviePy text/subtitles
RUN sed -i 's/rights="none" pattern="@\*"/rights="read|write" pattern="@*"/' /etc/ImageMagick-6/policy.xml || true

# Download Montserrat ExtraBold directly from Google Fonts
RUN wget -q https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/static/Montserrat-ExtraBold.ttf -O /usr/share/fonts/Montserrat-ExtraBold.ttf || true

RUN fc-cache -f -v

# Create a non-root user required by Hugging Face Spaces
RUN useradd -m -u 1000 user

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend and frontend files to the container
COPY --chown=user:user . /app/zipclip-backend/

USER user
WORKDIR /app/zipclip-backend
EXPOSE 7860
ENV PORT=7860
CMD ["python", "api.py"]