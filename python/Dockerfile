# Silk Screen Python Engine - Docker Image

FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY core/ ./core/
COPY utils/ ./utils/
COPY config/ ./config/
COPY main.py .

# Create output directory
RUN mkdir -p /app/output

# Set volume for input/output
VOLUME ["/app/input", "/app/output"]

# Run as non-root user
RUN useradd -m -u 1000 silk_screen && \
    chown -R silk_screen:silk_screen /app
USER silk_screen

# Default command
ENTRYPOINT ["python", "main.py"]
CMD ["--help"]
