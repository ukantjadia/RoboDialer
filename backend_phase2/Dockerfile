FROM python:3.10-slim

# 🔧 Install only essential system dependencies for API calls
RUN apt-get update && apt-get install -y \
    wget unzip curl gnupg lsb-release ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# 🌍 Set environment variables
ENV PYTHONPATH=/app

# 📁 Set working directory
WORKDIR /app

# 📦 Copy the entire project (including backend_phase2 & scraper modules)
COPY . .

# 📥 Install Python dependencies
RUN pip install --no-cache-dir -r backend_phase2/requirements.txt

# 🚀 Set working dir to API entrypoint and start app
WORKDIR /app/backend_phase2/api
CMD ["python", "app.py"]
