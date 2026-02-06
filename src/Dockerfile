FROM python:3.12.3-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Ho_Chi_Minh

# ---- System dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tzdata \
        ffmpeg \
        netcat-openbsd \
        ca-certificates \
        curl \
        build-essential \
        poppler-utils \
        ghostscript \
        qpdf \
        # Cài đặt LibreOffice Headless
        libreoffice \
        libreoffice-writer \
        libreoffice-java-common \
        # Cài đặt font để hiển thị đúng tiếng Việt và ký tự đặc biệt
        fonts-liberation \
        fonts-dejavu \
        fontconfig \
    && ln -fs /usr/share/zoneinfo/$TZ /etc/localtime \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ---- Upgrade pip tools
RUN python -m pip install --upgrade pip setuptools wheel

WORKDIR /app
COPY requirements.txt .

# ---- Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ---- Copy source code
COPY . .

EXPOSE 8000