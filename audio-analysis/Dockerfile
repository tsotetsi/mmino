FROM python:3.11-slim

ARG ENVIRONMENT=production
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg libsndfile1 libportaudio2 curl && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
COPY audio-analysis/requirements ./requirements/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements/base.txt

RUN if [ "$ENVIRONMENT" = "local" ]; then \
      pip install --no-cache-dir -r requirements/local.txt; \
    else \
      pip install --no-cache-dir -r requirements/production.txt; \
    fi

COPY audio-analysis/alembic.ini .
COPY audio-analysis/mmino ./mmino

RUN groupadd -r appgroup && \
    useradd -r -g appgroup -s /bin/false appuser && \
    chown -R appuser:appgroup /app
USER appuser

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn mmino.main:app --host 0.0.0.0 --port 8000"]