#!/bin/bash

# --- CONFIGURATION ---
domains=(mmino.com)
email="thapelo@mmnino.com"
data_path="./certbot"
docker_compose_file="docker-compose.yml"
# ---------------------

if [ ! -e "$data_path/conf/ssl-dhparams.pem" ]; then
  echo "### Downloading recommended TLS parameters..."
  mkdir -p "$data_path/conf"
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "$data_path/conf/options-ssl-nginx.conf"
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "$data_path/conf/ssl-dhparams.pem"
fi

echo "### Creating dummy certificate for $domains..."
path="/etc/letsencrypt/live/$domains"
mkdir -p "$data_path/conf/live/$domains"
docker compose -f $docker_compose_file run --rm --entrypoint \
  "openssl req -x509 -nodes -newkey rsa:4096 -days 1\
    -keyout '$path/privkey.pem' \
    -out '$path/fullchain.pem' \
    -subj '/CN=localhost'" certbot

echo "### Starting nginx..."
docker compose -f $docker_compose_file up --force-recreate -d nginx

echo "### Deleting dummy certificate for $domains..."
docker compose -f $docker_compose_file run --rm --entrypoint \
  "rm -rf /etc/letsencrypt/live/$domains /etc/letsencrypt/archive/$domains /etc/letsencrypt/renewal/$domains.conf" certbot

echo "### Requesting real Let's Encrypt certificate for $domains..."
# Join domains with -d
domain_args=""
for domain in "${domains[@]}"; do
  domain_args="$domain_args -d $domain"
done

docker compose -f $docker_compose_file run --rm --entrypoint \
  "certbot certonly --webroot -w /var/www/certbot \
    --email $email --agree-tos --no-eff-email \
    $domain_args" certbot

echo "### Reloading nginx to pick up real certificates..."
docker compose -f $docker_compose_file exec nginx nginx -s reload

echo "### Setup Complete!"