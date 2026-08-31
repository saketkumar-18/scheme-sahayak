FROM python:3.11-slim AS base

WORKDIR /app

# Install deps first for layer caching
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# App code + data
COPY backend/app /app/app
COPY backend/data /app/data
COPY backend/scripts /app/scripts
COPY backend/tests /app/tests

# Non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
