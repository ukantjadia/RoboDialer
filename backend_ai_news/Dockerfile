# Use official Python image
FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose Flask port
EXPOSE 5100

# Set environment variable for Flask
ENV FLASK_APP=api.app:app

# Run the app
CMD ["flask", "run", "--host=0.0.0.0", "--port=5100"] 