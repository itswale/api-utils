# Use an official Python runtime as the base image
FROM python:3.9-slim

# Set working directory in the container
WORKDIR /app

# Install system dependencies required for Playwright and Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxkbcommon0 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libasound2 \
    libegl1 \
    libfontconfig1 \
    fonts-liberation \
    libu2f-udev \
    libvulkan1 \
    xfonts-base \
    xfonts-scalable \
    xvfb \
    ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy requirements file first (optimization for caching)
COPY requirements.txt .

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Install Playwright browsers as root and verify installation
RUN playwright install chromium && \
    ls -la /root/.cache/ms-playwright/ && \
    python -c "from playwright.sync_api import sync_playwright; with sync_playwright() as p: browser = p.chromium.launch(headless=True); browser.close()" || { echo "Chromium launch failed during build"; exit 1; }

# Create a non-root user and copy Playwright binaries
RUN useradd -m -r appuser && \
    mkdir -p /home/appuser/.cache/ms-playwright && \
    cp -r /root/.cache/ms-playwright/* /home/appuser/.cache/ms-playwright/ && \
    chown -R appuser:appuser /home/appuser/.cache/ms-playwright /app
USER appuser

# Copy the rest of your application code
COPY . .

# Expose the port Render runs on
EXPOSE 8501

# Command to run the Streamlit app with xvfb for headless support
ENTRYPOINT ["xvfb-run", "streamlit", "run"]
CMD ["app.py", "--server.port=8501", "--server.address=0.0.0.0"]