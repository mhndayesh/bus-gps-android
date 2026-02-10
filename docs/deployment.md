# 🚀 Deployment Guide

## 🛠️ Local Development (Recommended)

### Prerequisites
- Docker & Docker Compose
- Git

### Steps
1.  **Clone Repository:**
    ```bash
    git clone https://github.com/mhndayesh/bus-gps-system.git
    cd bus-gps-system
    ```

2.  **Run with Docker Compose:**
    ```bash
    docker-compose up --build
    ```

3.  **Access Application:**
    - App: `http://localhost:5000`
    - PGAdmin (Database GUI): `http://localhost:5050` (Email: `user@domain.com`, Pass: `password`)

---

## ☁️ Cloud Deployment (Railway)

### Recommended Services
- **Railway:** Hosting for PostgreSQL, Redis, and Python Service.
- **HiveMQ Cloud:** Free MQTT Broker for real-time messaging.

### Steps
1.  **Fork Repo:** Fork this project to your GitHub.
2.  **Create Project on Railway:**
    - Click **"New Project"** -> **"Deploy from GitHub"**.
    - Select your forked repo.
3.  **Add Database (PostgreSQL):**
    - In Railway canvas, right-click -> **Add Service** -> **PostgreSQL**.
4.  **Configure Environment Variables:**
    - Go to your Web Service -> **Variables**.
    - Add the required variables (see below).

---

## 🔑 Environment Variables Reference

| Variable | Description | Default / Example |
|---|---|---|
| `FLASK_SECRET_KEY` | Crucial security key for sessions | *Generate using `python -c "import secrets; print(secrets.token_hex(32))"`* |
| `DB_HOST` | Database Hostname | `containers-us-west-1.railway.app` |
| `DB_NAME` | Database Name | `railway` |
| `DB_USER` | Database Username | `postgres` |
| `DB_PASS` | Database Password | `******` |
| `MQTT_BROKER` | HiveMQ Cluster URL | `your-cluster.s1.eu.hivemq.cloud` |
| `MQTT_USER` | MQTT Username | `myuser` |
| `MQTT_PASS` | MQTT Password | `******` |
| `CORS_ORIGINS` | Comma-separated allow list | `https://your-app.railway.app` |

---

## 🏗️ Docker Production Build

```dockerfile
# Dockerfile provided in root
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "web_app:app", "-b", "0.0.0.0:5000"]
```
