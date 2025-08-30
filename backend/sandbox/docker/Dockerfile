FROM mcr.microsoft.com/playwright/python:v1.47.2-jammy

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    netcat-traditional \
    gnupg \
    curl \
    unzip \
    zip \
    xvfb \
    libxss1 \
    libnss3 \
    libnspr4 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    xdg-utils \
    fonts-liberation \
    dbus \
    xauth \
    xvfb \
    x11vnc \
    tigervnc-tools \
    supervisor \
    net-tools \
    procps \
    git \
    python3-numpy \
    fontconfig \
    fonts-dejavu \
    fonts-dejavu-core \
    fonts-dejavu-extra \
    tmux \
    # Extra fonts for better rendering
    fonts-noto \
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    # PDF Processing Tools
    poppler-utils \
    # Document Processing Tools
    antiword \
    unrtf \
    catdoc \
    # Text Processing Tools
    grep \
    gawk \
    sed \
    # File Analysis Tools
    file \
    # Data Processing Tools
    jq \
    csvkit \
    xmlstarlet \
    # Media / Graph / Misc tools
    ffmpeg \
    graphviz \
    # Optional office converter (comment out if not needed)
    libreoffice \
    pandoc \
    # Additional Utilities
    less \
    vim \
    tree \
    rsync \
    lsof \
    iputils-ping \
    dnsutils \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Node is included in Playwright images; install wrangler if desired
RUN npm install -g npm@latest wrangler

# Install noVNC
RUN git clone https://github.com/novnc/noVNC.git /opt/novnc \
    && git clone https://github.com/novnc/websockify /opt/novnc/utils/websockify \
    && ln -s /opt/novnc/vnc.html /opt/novnc/index.html

# Set platform hint (can be overridden by builder)
ARG TARGETPLATFORM

# Set up working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server script
COPY . /app
COPY server.py /app/server.py
COPY browser_api.py /app/browser_api.py

# Playwright and Chromium are already installed in the base image
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    CHROME_PATH=/ms-playwright/chromium-*/chrome-linux/chrome \
    ANONYMIZED_TELEMETRY=false \
    DISPLAY=:99 \
    RESOLUTION=1920x1080x24 \
    VNC_PASSWORD=vncpassword \
    CHROME_PERSISTENT_SESSION=true \
    RESOLUTION_WIDTH=1920 \
    RESOLUTION_HEIGHT=1080

# Set up supervisor configuration
RUN mkdir -p /var/log/supervisor
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

EXPOSE 6080 5901 8000 8080 9222

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
