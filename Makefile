# Variables
DOCKER_COMPOSE_PROD = docker compose -f docker-compose.yml
DOCKER_COMPOSE_LOCAL = docker compose -f docker-compose.yml -f docker-compose.override.yml

.PHONY: help local-up local-down prod-init prod-up prod-down gen-pass logs

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --- LOCAL DEVELOPMENT ---
local-up: ## Start local development environment (No SSL)
	$(DOCKER_COMPOSE_LOCAL) up -d --build

local-down: ## Stop local environment
	$(DOCKER_COMPOSE_LOCAL) down

local-nuke: ## Nuke local environment (stop and remove all containers, networks, volumes)
	$(DOCKER_COMPOSE_LOCAL) down -v --remove-orphans

sys-prep: ## Fix Redis memory overcommit and system limits (Linux only)
	@echo "Configuring host system for Redis..."
	sudo sysctl vm.overcommit_memory=1
	@echo "vm.overcommit_memory = 1" | sudo tee -a /etc/sysctl.conf
	@echo "System prep complete."

# --- PRODUCTION ---
prod-init: sys-prep ## Run SSL bootstrap and system prep
	chmod +x init-ssl.sh
	./init-ssl.sh

prod-up: ## Start production environment (SSL + Auth)
	$(DOCKER_COMPOSE_PROD) up -d --build

prod-down: ## Stop production environment
	$(DOCKER_COMPOSE_PROD) down

# --- UTILITIES ---
gen-pass: ## Generate/Update .htpasswd (usage: make gen-pass user=admin pass=123)
	cd nginx && docker run --rm httpd:alpine htpasswd -nb $(user) $(pass) > .htpasswd
	@echo ".htpasswd generated successfully."

logs: ## View Nginx logs in real-time
	$(DOCKER_COMPOSE_PROD) logs -f nginx

reload: ## Reload Nginx configuration without downtime
	$(DOCKER_COMPOSE_PROD) exec nginx nginx -s reload

# --- Update Dependencies ---
update-deps: ## Update all Python dependencies
	@echo "Updating Python dependencies..."
	cd audio-analysis && pip-compile --upgrade requirements/base.in
	@echo "Dependencies updated."