FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY backend/requirements.txt .
# Upgrade pip first to get latest resolver and wheels
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the backend code
COPY backend/ .

# Set environment variable
ENV PYTHONPATH=/app

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["python", "app_main.py"]
