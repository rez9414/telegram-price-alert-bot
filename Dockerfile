FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py db.py ./

# alerts.db should live on a mounted volume in production
VOLUME ["/app/data"]
ENV DB_PATH=/app/data/alerts.db

CMD ["python", "bot.py"]
