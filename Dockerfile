# Use an official Python runtime as the base image
FROM python:3.9-slim

# Set working directory in the container
WORKDIR /app

# Install system dependencies required for Playwright and Chromium
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
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
    libdbus-1-3 \
    libegl1 \
    libfontconfig1 \
    fonts-liberation \
    libu2f-udev \
    libvulkan1 \
    xfonts-base \
    xfonts-scalable \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first (optimization for caching)
COPY requirements.txt .

# Upgrade pip and install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Install Playwright browsers as root
RUN playwright install chromium

# Create a non-root user and switch to it
RUN useradd -m -r appuser && chown appuser:appuser /app
USER appuser

# Copy the rest of your application code
COPY . .

# Expose the port Render runs on
EXPOSE 8501

# Command to run the Streamlit app with xvfb for headless support
ENTRYPOINT ["xvfb-run", "streamlit", "run"]
CMD ["app.py", "--server.port=8501", "--server.address=0.0.0.0"]