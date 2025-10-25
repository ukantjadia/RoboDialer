# =========================
# STAGE 1: Build environment
# =========================
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies for compiling any Python packages
RUN apt-get update --fix-missing && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        build-essential wget ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Copy only requirements for dependency installation
COPY requirements.txt .

# Install dependencies to a temporary directory
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --target=/app/deps -r requirements.txt && \
    pip uninstall -y jwt pyjwt && \
    pip install --no-cache-dir --target=/app/deps pyjwt==2.8.0


# =========================
# STAGE 2: Runtime environment
# =========================
FROM python:3.11-slim

WORKDIR /app

# Copy only required runtime files and preinstalled dependencies
COPY --from=builder /app/deps /usr/local/lib/python3.11/site-packages

# Copy your application source code
COPY . .

EXPOSE 8001

# Optional: uncomment if needed
# ENV FLASK_ENV=production

# Run the app
CMD ["python", "app.py"]
