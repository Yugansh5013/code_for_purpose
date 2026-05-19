FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies if required for compiling certain python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Render uses PORT env var (defaults to 10000)
# For local Docker: docker run -p 8000:8000 -e PORT=8000 ...
EXPOSE ${PORT:-10000}

# Command to run the application
CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-10000}
