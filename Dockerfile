# Python 3.11 - compatible with spaCy & numpy
FROM python:3.11-slim

# Runtime env vars
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy app source
COPY . .

# Render port
EXPOSE 10000

# Run with Gunicorn (PRODUCTION SAFE)
CMD ["gunicorn", "app:app", "--workers", "1", "--threads", "2", "--timeout", "120"]
