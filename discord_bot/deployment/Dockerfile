FROM --platform=linux/amd64 python:3.13

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install only what we need (apt-utils already included in full image)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY config/discord_bot_requirements.txt .
RUN pip install --no-cache-dir --root-user-action=ignore -r discord_bot_requirements.txt

# Create config directory and empty credentials file (will be overwritten by volume mount)
RUN mkdir -p /app/config && echo "{}" > /app/config/credentials.json

# Copy shared package first
COPY ../shared ./shared

# Set PYTHONPATH to include shared packages (needed for from shared.firestore import ...)
ENV PYTHONPATH=/app:$PYTHONPATH

# Copy all bot files
COPY . .

# Make entrypoint executable
RUN chmod +x /app/deployment/entrypoint.sh

# Expose port for health check
EXPOSE 8080

# Run the entrypoint script
CMD ["/app/deployment/entrypoint.sh"] 