# MminoIO Audio Processing API

> <b>MminoIO</b> is a robust, scalable, and efficient audio processing API designed for handling asynchronous file uploads, processing, and management. Built with a modern Python stack, it leverages FastAPI for high-performance web endpoints, Celery for distributed task queuing, and a suite of powerful tools to ensure reliability and scalability.

<div align="center">
    <img src="/mmino-logo.svg" alt="mmino logo" width="200" height="200">
</div>

<div align="center">

[![Build Status](https://img.shields.io/github/actions/workflow/status/tsotetsi/mmino/ci-cd.yml?branch=main&logo=github&style=flat)](https://github.com/tsotetsi/mmino/actions)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.14+-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.131.0-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Pydantic](https://img.shields.io/badge/-Pydantic_v2-E92063?logo=Pydantic)](https://docs.pydantic.dev/latest/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-blue?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17+-316192?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7+-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Celery](https://img.shields.io/badge/Celery-5.6.9-379683?logo=celery&logoColor=white)](https://docs.celeryq.dev/en/stable/)
[![gitleaks-badge](https://img.shields.io/badge/protected%20by-gitleaks-blue)](https://gitleaks.io/)
[![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=white)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Vite](https://img.shields.io/badge/Vite-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

</div>

## ✨ Key Features

- **Asynchronous File Uploads**: Non-blocking endpoints for uploading large audio, video, and image files.
- **Distributed Task Processing**: Uses Celery and Redis to manage a queue of processing jobs, allowing for horizontal scaling of workers.
- **Real-time Job Updates**: WebSocket integration to provide clients with live progress updates on their processing jobs.
- **Secure Authentication**: API key-based authentication and user management.
- **Rate Limiting**: Protects the API from abuse with configurable request throttling.
- **Object Storage**: Integrates with MinIO (or any S3-compatible service) for durable file storage.
- **Robust Database Backend**: Uses PostgreSQL with SQLAlchemy for data persistence and Alembic for database migrations.
- **Containerized & Production-Ready**: Fully containerized with Docker and Docker Compose for easy deployment and orchestration.
- **Secure by Design**: Manages secrets via Docker Secrets and includes a secure Nginx reverse proxy with SSL support.

## 🛠️ Technology Stack

- **Backend**: Python, FastAPI, Pydantic, SQLAlchemy
- **Database**: PostgreSQL
- **Cache & Message Broker**: Redis
- **Task Queue**: Celery
- **Object Storage**: MinIO
- **Migrations**: Alembic
- **Web Server**: Uvicorn, Nginx (Reverse Proxy)
- **Containerization**: Docker, Docker Compose

## 📋 Prerequisites

Before you begin, ensure you have the following installed:
- [Docker](https://www.docker.com/get-started)
- [Docker Compose](https://docs.docker.com/compose/install/)

## ⚙️ Configuration

1.  **Environment Variables**:
    Create a `.env` file by copying the `example.env` file:
    ```bash
    cp example.env .env
    ```
    Update the `.env` file with your desired configuration, such as project settings, database names, and external-facing domains.

2.  **Secrets**:
    The application uses Docker Secrets for sensitive credentials. Create the following files inside the `.secrets/` directory:
    - `postgres_user.txt`: Username for the main PostgreSQL database user.
    - `postgres_password.txt`: Password for the main PostgreSQL database user.
    - `redis_password.txt`: Password for Redis authentication.
    - `minio_root_user.txt`: Root user for the MinIO object storage.
    - `minio_root_password.txt`: Root password for the MinIO object storage.
    - `healthcheck_user.txt`: A dedicated user for database health checks.
    - `healthcheck_password.txt`: Password for the health check user.
    - `mmino_app_password.txt`: Password for the application user within the database.

    You can use the following command to quickly generate a strong password:
    ```bash
    mkdir -p .secrets && openssl rand -base64 32 > .secrets/your_secret_file.txt
    ```

## 🚀 Installation & Running

Once the prerequisites and configuration are complete, you can build and run the application using Docker Compose:

```bash
docker-compose up -d --build
```

This command will:
- Build the Docker images for the API, worker, and other services.
- Start all services in detached mode.
- Create the necessary Docker volumes and networks.
- Apply database migrations automatically on startup.

To view the logs for all running services:
```bash
docker-compose logs -f
```

To stop the services:
```bash
docker-compose down
```

### Running the Frontend Separately

If you wish to run the frontend application independently (e.g., for development purposes):

1.  **Navigate to the frontend directory**:
    ```bash
    cd frontend
    ```

2.  **Install dependencies**:
    ```bash
    npm install
    ```

3.  **Start the development server**:
    ```bash
    npm run dev
    ```
    The frontend application will typically be available at `http://localhost:5173` (or another port if 5173 is in use).

## 🌐 API Usage

- **API Documentation**: Once the application is running, the interactive Swagger UI documentation is available at `http://localhost/docs`.
- **MinIO**: The MinIO object storage is available at `http://localhost:9000`. Use the credentials from the `.secrets/` directory to log in.
- **Flower**: The Celery task monitoring dashboard is available at `http://localhost:5555`. Use the credentials from the `.secrets/` directory to log in.
- **Health Check**: A health check endpoint is available at `http://localhost/health`.
- **API Prefix**: All API v1 endpoints are prefixed with `/api/v1`.
- **Frontend**: The frontend application is available at `http://localhost:5173` (or another port if 5173 is in use).

## Simple Development Flow Testing for Kubernetes

- **The Steps**:
- **Switch Context**: eval $(minikube docker-env) (This tells your terminal: "Use Minikube's Docker, not my laptop's.")
- **Build**: docker build -t mmino-api:latest -f audio-analysis/Dockerfile .
- **Deploy**: kubectl apply -f minikube-dev.yaml
- **Note**: Ensure your manifest has imagePullPolicy: Never so K8s doesn't try to look for it online.

### Minikube

If you are running the application on Minikube, you can access the services using the following commands:

- **API**: `minikube service api --url`
- **Frontend**: `minikube service frontend --url`
- **MinIO**: `minikube service minio --url`
- **Flower**: `minikube service flower --url`

## ⚖️ License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.