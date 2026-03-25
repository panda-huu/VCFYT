FROM python:3.10-slim

# Install audio and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libportaudio2 \
    libasound2-dev \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
# Create requirements.txt containing: pyrogram, pytgcalls, librosa, sounddevice, numpy, tgcrypto
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run the script
CMD ["python", "main.py"]
