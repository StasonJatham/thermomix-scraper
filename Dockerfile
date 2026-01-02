FROM python:3.12-slim

# Install Chromium and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Set Chrome path
ENV GOOGLE_CHROME_PATH=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY thermomix_scraper/ ./thermomix_scraper/

# Create data directory
RUN mkdir -p /data

# Default environment
ENV THERMOMIX_OUTPUT=/data
ENV THERMOMIX_HEADLESS=true

ENTRYPOINT ["python", "-m", "thermomix_scraper"]
