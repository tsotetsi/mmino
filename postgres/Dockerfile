FROM postgres:17

LABEL org.opencontainers.image.source="https://mmino.github.io/mmino" \
      org.opencontainers.image.description="Production PostgreSQL 17" \
      maintainer="tsotetsi@mmino.io"

# Create and set permissions for runtime directory
USER root
# Runtime directory + cleanup
RUN mkdir -p /var/run/postgresql && \
    chown postgres:postgres /var/run/postgresql && \
    chmod 0755 /var/run/postgresql && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

USER postgres