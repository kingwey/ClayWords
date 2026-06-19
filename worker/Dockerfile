FROM nvidia/cuda:12.2-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install Python and system dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip3 install --no-cache-dir \
    torch==2.2.0 \
    torchvision \
    trimesh==4.1.0 \
    open3d==0.18.0 \
    arq==0.26.0 \
    structlog==24.1.0 \
    httpx==0.27.0

WORKDIR /app
COPY . /app

CMD ["python3", "main.py"]
