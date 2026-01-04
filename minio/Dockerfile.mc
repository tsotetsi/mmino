# Stage 1: Get official client source.
FROM minio/mc:latest AS mc-source

# Stage 2: Build runner.
FROM alpine:latest

# Get bash for creating buckets and curl for health check.
RUN apk add --no-cache bash curl ca-certificates

COPY --from=mc-source /usr/bin/mc /usr/bin/mc

RUN chmod +x /usr/bin/mc

ENTRYPOINT ["/bin/bash"]