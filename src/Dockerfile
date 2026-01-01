FROM python:3.12.3

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y ffmpeg netcat-openbsd && apt-get clean

WORKDIR /app
COPY . /app/

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir python-multipart

EXPOSE 8000