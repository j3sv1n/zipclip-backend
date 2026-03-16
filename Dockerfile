# Use a standard Python image for CPU-only deployment
FROM python:3.10-slim

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    ffmpeg \
    imagemagick \
    libavdevice-dev \
    libavfilter-dev \
    libopus-dev \
    libvpx-dev \
    pkg-config \
    libsrtp2-dev \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Fix ImageMagick security policy for subtitle rendering
RUN sed -i 's/rights="none" pattern="@\*"/rights="read|write" pattern="@*"/' /etc/ImageMagick-*/policy.xml

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
# Note: Since this is CPU-only, we might want to install torch-cpu version to save space
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create output and upload directories
RUN mkdir -p /app/output_videos /app/uploads

# Expose the API port
EXPOSE 7860

# Default command to run the API server
# Hugging Face Spaces expects the app to run on port 7860 by default
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "7860"]
