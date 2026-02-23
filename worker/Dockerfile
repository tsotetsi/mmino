FROM python:3.14-slim

# Install ffmpeg with more codecs
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    libavcodec-extra \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY audio-analysis/mmino ./mmino

RUN groupadd -r appgroup && \
    useradd -r -g appgroup -s /bin/false worker && \
    chown -R worker:appgroup /app

USER worker

CMD ["celery", "-A", "worker.tasks", "worker", "--loglevel=info"]