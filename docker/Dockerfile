# Purpose: Containerize FuelOps FastAPI inference service
# Base: python:3.11-slim | Port: 8000 | User: non-root appuser

FROM python:3.11-slim

WORKDIR /app

# Install deps first (layer caching  only rebuilds if requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY main.py .

# Non-root user for security
RUN adduser --disabled-password --gecos '' appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

INVALID_INSTRUCTION this will break the build
