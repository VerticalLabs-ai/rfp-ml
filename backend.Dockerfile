# Use Python 3.12 slim image for a small footprint
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/app/api

# Install system dependencies (required for some python packages and playwright)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl --version

# Install uv for faster dependency management
RUN pip install uv

# Copy requirements
COPY requirements.txt .
COPY requirements_api.txt .

# Install Python dependencies
# We merge both requirement files to ensure all ML and API deps are present
RUN uv pip install --system --no-cache -r requirements.txt -r requirements_api.txt

# Install Playwright browsers (if needed for backend automation)
RUN playwright install --with-deps chromium

# Copy application code
# We copy the entire project to ensure `src/` and `api/` are available
COPY . .

# Create directory for SQLite db and logs
RUN mkdir -p api/data logs

# Expose port
EXPOSE 8000

# Run the application
# We point to app.main:app (since /app/api is in PYTHONPATH) and reload is disabled for production
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
