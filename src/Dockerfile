FROM nvidia/cuda:12.3.2-runtime-ubuntu22.04

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Ho_Chi_Minh

# ---- System deps (stable, cache tốt)
RUN ln -fs /usr/share/zoneinfo/$TZ /etc/localtime \
    && apt-get update \
    && apt-get install -y \
        tzdata \
        software-properties-common \
        ffmpeg \
        netcat-openbsd \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y \
        python3.12 \
        python3.12-dev \
        python3.12-venv \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 \
    && update-alternatives --set python3 /usr/bin/python3.12

RUN python3.12 -m ensurepip --upgrade \
    && python3.12 -m pip install --upgrade pip setuptools wheel

WORKDIR /app

# ---- COPY requirements trước (cache cực tốt)
COPY requirements.txt .

# ---- Cài dependency nặng trước
RUN --mount=type=cache,target=/root/.cache/pip \
    python3 -m pip install \
        torch torchvision torchaudio \
        --index-url https://download.pytorch.org/whl/cu121 \
    && python3 -m pip install onnxruntime-gpu \
    && python3 -m pip install -r requirements.txt \
    && python3 -m pip install python-multipart

# ---- COPY source code sau cùng
COPY . .

EXPOSE 8000