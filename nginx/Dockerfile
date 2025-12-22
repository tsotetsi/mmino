# Use a specific version for reproducibility
FROM nginx:1.28-alpine

# Remove default configuration
RUN rm /etc/nginx/conf.d/default.conf

# Copy our custom configuration
# Note: Ensure your config file is named nginx.conf
COPY nginx.conf /etc/nginx/nginx.conf

# Create the shared_data directory to avoid startup errors
RUN mkdir -p /shared_data/downloads && \
    chown -R nginx:nginx /shared_data

# Set working directory
WORKDIR /usr/share/nginx/html

# Healthcheck to ensure the container is actually serving requests
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost/health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]