# Use Python 3.11 (spaCy & blis compatible)
FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN python -m spacy download en_core_web_sm

COPY . .

CMD ["gunicorn", "app:app", "--workers", "1", "--threads", "2", "--timeout", "120"]
