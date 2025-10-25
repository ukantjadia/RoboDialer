FROM python:3.10-slim

WORKDIR /app

COPY . .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

EXPOSE 5000
CMD ["uvicorn", "backend.api.app:app", "--host", "0.0.0.0", "--port", "5000"]

