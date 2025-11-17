# Deployment Guide: RFP Dashboard & Submission Agent

**Date**: November 14, 2025
**Version**: 1.0.0

## Overview

This guide covers deploying the complete RFP Bid Generation Dashboard and Submission Agent system.

## System Components

1. **Backend API** (FastAPI) - Port 8000
2. **Frontend Dashboard** (React + Vite) - Port 3000
3. **Database** (SQLite/PostgreSQL)
4. **Submission Agent** (Background worker)
5. **WebSocket Server** (Real-time updates)

## Prerequisites

### Software Requirements

- Python 3.8+
- [uv](https://docs.astral.sh/uv/) - Fast Python package installer and resolver
- Node.js 18+
- npm or yarn
- Git

### Environment Variables

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL=sqlite:///./rfp_dashboard.db
# For PostgreSQL: postgresql://user:password@localhost/rfp_dashboard

# Redis (optional, for task queue)
REDIS_URL=redis://localhost:6379/0

# API Keys
SAM_GOV_API_KEY=your_sam_gov_api_key
HUGGINGFACE_API_KEY=your_huggingface_key (if using)
OPENAI_API_KEY=your_openai_key (if using)

# SMTP for email notifications
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Slack webhook
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Security
SECRET_KEY=your-secret-key-change-this-in-production
```

## Quick Start (Development)

### 1. Install Dependencies

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh  # macOS/Linux
# Or: pip install uv

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# Or: .venv\Scripts\activate on Windows

# Install backend dependencies
uv pip install -r requirements.txt
uv pip install -r requirements_api.txt

# Frontend dependencies
cd frontend
npm install
cd ..
```

### 2. Initialize Database

```bash
cd api
python -c "from app.core.database import init_db; init_db()"
cd ..
```

### 3. Start Backend

```bash
# Option 1: Using script
chmod +x scripts/start_backend.sh
./scripts/start_backend.sh

# Option 2: Manual
cd api
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: http://localhost:8000
API docs at: http://localhost:8000/docs

### 4. Start Frontend

```bash
# Option 1: Using script
chmod +x scripts/start_frontend.sh
./scripts/start_frontend.sh

# Option 2: Manual
cd frontend
npm run dev
```

Frontend will be available at: http://localhost:3000

### 5. Test Submission Agent

```bash
chmod +x scripts/test_submission_agent.py
python scripts/test_submission_agent.py
```

## Production Deployment

### Docker Deployment

**1. Create Dockerfile for Backend:**

```dockerfile
# api/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv for faster dependency installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY requirements_api.txt .
RUN uv pip install --system --no-cache -r requirements_api.txt

COPY app ./app
COPY ../src ./src

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**2. Create Dockerfile for Frontend:**

```dockerfile
# frontend/Dockerfile
FROM node:18-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
```

**3. Docker Compose:**

```yaml
# docker-compose.yml
version: "3.8"

services:
  backend:
    build: ./api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/rfp_dashboard
      - REDIS_URL=redis://redis:6379/0
    env_file:
      - .env
    depends_on:
      - db
      - redis

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=rfp_dashboard
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

**4. Deploy:**

```bash
docker-compose up -d
```

### Manual Production Deployment

**1. Backend (with Gunicorn):**

```bash
# Activate virtual environment
source .venv/bin/activate

# Install production server
uv pip install gunicorn

# Start with multiple workers
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile -
```

**2. Frontend (Build and Serve):**

```bash
cd frontend
npm run build

# Serve with nginx or any static file server
# The build output is in frontend/dist/
```

**3. Nginx Configuration:**

```nginx
# /etc/nginx/sites-available/rfp-dashboard
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        root /var/www/rfp-dashboard/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Process Management (PM2)

```bash
# Install PM2
npm install -g pm2

# Start backend
pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 8000" --name rfp-backend

# Start submission agent worker
pm2 start "python -m src.agents.submission_worker" --name submission-agent

# Save configuration
pm2 save
pm2 startup
```

## Monitoring & Maintenance

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Check database connection
python -c "from api.app.core.database import engine; print(engine.connect())"
```

### Logs

```bash
# Backend logs (PM2)
pm2 logs rfp-backend

# Frontend logs (PM2 if running with PM2)
pm2 logs rfp-frontend

# Submission agent logs
tail -f logs/submission_agent.log
```

### Database Backups

```bash
# SQLite backup
cp rfp_dashboard.db rfp_dashboard_backup_$(date +%Y%m%d).db

# PostgreSQL backup
pg_dump rfp_dashboard > backup_$(date +%Y%m%d).sql
```

## Troubleshooting

### Backend Won't Start

```bash
# Check Python version
python --version  # Should be 3.8+

# Activate virtual environment
source .venv/bin/activate

# Check dependencies
uv pip list | grep fastapi

# Check database
python -c "from app.core.database import init_db; init_db()"
```

### Frontend Build Errors

```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Check Node version
node --version  # Should be 18+
```

### WebSocket Connection Fails

- Check CORS settings in `api/app/core/config.py`
- Verify WebSocket proxy configuration in nginx
- Check firewall rules for port 8000

## Security Checklist

- [ ] Change SECRET_KEY in production
- [ ] Use HTTPS in production
- [ ] Rotate API keys regularly
- [ ] Enable database encryption
- [ ] Set up rate limiting
- [ ] Configure firewall rules
- [ ] Enable audit logging
- [ ] Backup encryption keys securely

## Performance Tuning

### Backend

- Increase Gunicorn workers: `--workers <num_cpu_cores * 2 + 1>`
- Enable database connection pooling
- Add Redis for caching
- Use PostgreSQL instead of SQLite for production

### Frontend

- Enable gzip compression in nginx
- Set proper cache headers
- Use CDN for static assets
- Enable HTTP/2

## Support

For issues or questions:

- Check logs first
- Review documentation at `/docs`
- Open an issue on GitHub

---

**Version**: 1.0.0
**Last Updated**: November 14, 2025
