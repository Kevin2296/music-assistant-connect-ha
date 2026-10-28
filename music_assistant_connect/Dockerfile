# Multi-architecture Chromium image. The first build is large; Chromium runs only on demand.
FROM mcr.microsoft.com/playwright/python:v1.63.0-noble
ARG BUILD_VERSION=0.6.0
ARG BUILD_ARCH=amd64
LABEL io.hass.version="${BUILD_VERSION}" \
      io.hass.type="app" \
      io.hass.arch="${BUILD_ARCH}"
WORKDIR /opt/ma-connect
RUN apt-get update && apt-get install -y --no-install-recommends xvfb xdotool \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY startup.py ./startup.py
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 HOME=/tmp
# Read root-only options at startup, then switch to pwuser before serving HTTP.
USER root
EXPOSE 8675
CMD ["python", "/opt/ma-connect/startup.py"]
