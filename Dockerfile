# Use Python 3.11 (spaCy & blis compatible)
FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt


COPY . .

CMD ["gunicorn", "app:app", "--workers", "1", "--threads", "2", "--timeout", "120"]
