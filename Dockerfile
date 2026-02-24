# ======================================================
# 🧩 base image
# ======================================================
FROM ultralytics/ultralytics:latest-jetson-jetpack6@sha256:dee7b672e7ef818c508acc241368d7e27cb75f2cf6b2986c3cae871506adaf9b
RUN sed -i 's|http://ports.ubuntu.com/ubuntu-ports|http://free.nchc.org.tw/ubuntu-ports|g' /etc/apt/sources.list


# ======================================================
# ⚙️ 重新匯入 NVIDIA Jetson L4T repo 與 GPG key
# ======================================================
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl gnupg && \
    curl -fsSL https://repo.download.nvidia.com/jetson/jetson-ota-public.asc \
      | gpg --dearmor -o /usr/share/keyrings/nvidia-jetson.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/nvidia-jetson.gpg] https://repo.download.nvidia.com/jetson/common r36.2 main" > /etc/apt/sources.list.d/nvidia-l4t-apt-source.list && \
    echo "deb [signed-by=/usr/share/keyrings/nvidia-jetson.gpg] https://repo.download.nvidia.com/jetson/t234 r36.2 main" >> /etc/apt/sources.list.d/nvidia-l4t-apt-source.list

# ======================================================
# 🚀 更新系統並
# ======================================================
#RUN echo "deb http://ports.ubuntu.com/ubuntu-ports jammy main restricted universe multiverse" > /etc/apt/sources.list && \
#    echo "deb http://ports.ubuntu.com/ubuntu-ports jammy-updates main restricted universe multiverse" >> /etc/apt/sources.list && \
#    echo "deb http://ports.ubuntu.com/ubuntu-ports jammy-security main restricted universe multiverse" >> /etc/apt/sources.list && \
#    echo "deb http://ports.ubuntu.com/ubuntu-ports jammy-backports main restricted universe multiverse" >> /etc/apt/sources.list && \
#    apt-get clean

# ======================================================
# System utilities (for debugging, networking, editing)
# ======================================================
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    iproute2 \
    net-tools \
    iputils-ping \
    dnsutils \
    curl \
    wget \
    less \
    vim \
    nano \
 && apt-get clean && rm -rf /var/lib/apt/lists/*








# ======================================================
# GStreamer core components
# ======================================================
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    gstreamer1.0-gl \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# ======================================================
# Python + OpenCV (no GUI)
# ======================================================
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3-opencv \
    libopencv-videoio-dev \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# ======================================================
# Optional: Python GStreamer bindings (for gst-python)
# ======================================================
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3-gi \
    gir1.2-gstreamer-1.0 \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

# ====================================================
# pip requirements.txt
# ====================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    python3-distutils \
    python3-setuptools \
 && rm -rf /var/lib/apt/lists/*


# ----------------------------------------------------
# 📂 6. 放入 YOLO 模型與程式
# ----------------------------------------------------
WORKDIR /workspace
COPY requirements.txt /workspace/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# RUN pip install --no-cache-dir --no-build-isolation lap==0.4.0


CMD ["python3", "main.py"]

