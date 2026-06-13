FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y \
    libreoffice \
    libreoffice-writer \
    libreoffice-draw \
    libreoffice-impress \
    libreoffice-java-common \
    poppler-utils \
    fonts-liberation \
    fonts-dejavu \
    --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py .

EXPOSE 10000
CMD gunicorn --bind 0.0.0.0:$PORT app:app
