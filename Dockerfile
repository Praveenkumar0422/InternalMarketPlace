# Use Python 3.11 (spaCy & blis compatible)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements.txt .

# Upgrade pip and install dependencies
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Copy remaining project files
COPY . .

# Expose port (Render uses 10000 internally)
EXPOSE 10000

# Start Flask app using gunicorn
CMD ["gunicorn", "app:app", "--workers", "1", "--threads", "2", "--timeout", "120"]
