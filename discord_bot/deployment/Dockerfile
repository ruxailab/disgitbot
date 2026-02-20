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
COPY requirements.txt .

# Copy only requirements files first to leverage Docker layer cache
COPY pr_review/requirements.txt ./pr_review/requirements.txt

# Upgrade pip to latest version to avoid upgrade notices
RUN pip install --no-cache-dir --upgrade pip

# Install dependencies from both requirements files
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt -r pr_review/requirements.txt

# Copy pr_review package (copied into build context by deploy script)
COPY pr_review ./pr_review

# Create config directory and empty credentials file (will be overwritten by volume mount)
RUN mkdir -p /app/config && echo "{}" > /app/config/credentials.json

# Copy shared package first (copied into build context by deploy script)
COPY shared ./shared

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