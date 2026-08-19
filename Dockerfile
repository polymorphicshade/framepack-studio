ARG CUDA_VERSION=12.4.1

FROM nvidia/cuda:${CUDA_VERSION}-runtime-ubuntu22.04

ARG CUDA_VERSION

RUN apt-get update && apt-get install -y \
    python3 python3-pip git ffmpeg wget curl && \
    pip3 install --upgrade pip

WORKDIR /app

# This allows caching pip install if only code has changed
COPY requirements.txt .

# Install dependencies
RUN pip3 install --no-cache-dir -r requirements.txt
RUN export CUDA_SHORT_VERSION=$(echo "${CUDA_VERSION}" | sed 's/\.//g' | cut -c 1-3) && \
    pip3 install --no-cache-dir torch torchvision torchaudio --index-url "https://download.pytorch.org/whl/cu${CUDA_SHORT_VERSION}"

# Attention backend.
#
# diffusers_helper/models/hunyuan_video_packed.py picks the fastest backend it
# can import - SageAttention > Flash Attention > xFormers > PyTorch SDPA - and
# prints its choice at startup. Nothing else in this image installs one, so
# without this the container generates on SDPA.
#
# SageAttention 1.0.6 is pure Triton, and Triton ships with the Linux torch
# wheels, so it compiles nothing and needs no CUDA toolkit - which matters here,
# because this is a -runtime base image with no nvcc. It must come after torch
# so it picks up that Triton.
#
# Build with --build-arg INSTALL_SAGEATTENTION=false to skip it. A failure is
# not fatal: the app falls back to SDPA and says so in its startup log.
ARG INSTALL_SAGEATTENTION=true
RUN if [ "${INSTALL_SAGEATTENTION}" = "true" ]; then \
        pip3 install --no-cache-dir "sageattention==1.0.6" \
        || echo "WARNING: SageAttention install failed - generation will fall back to PyTorch SDPA."; \
    fi

# Copy the source code to /app
COPY . .

VOLUME [ "/app/.framepack", "/app/outputs", "/app/loras", "/app/hf_download", "/app/modules/toolbox/model_esrgan", "/app/modules/toolbox/model_rife" ]

EXPOSE 7860

CMD ["python3", "studio.py"]
