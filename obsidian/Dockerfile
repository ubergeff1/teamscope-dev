FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DISPLAY=:1
ENV VNC_PORT=5900
ENV NOVNC_PORT=6080
ENV RESOLUTION=1920x1080x24

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl ca-certificates \
    xvfb x11vnc fluxbox \
    novnc websockify \
    libgtk-3-0 libnotify4 libnss3 libxss1 libasound2t64 \
    libgbm1 libsecret-1-0 libfuse2t64 desktop-file-utils \
    xdg-utils fonts-noto-core fonts-noto-color-emoji \
    procps supervisor dbus-x11 \
    && rm -rf /var/lib/apt/lists/*

# Download and install Obsidian AppImage
ARG OBSIDIAN_VERSION=1.8.9
RUN wget -q "https://github.com/obsidianmd/obsidian-releases/releases/download/v${OBSIDIAN_VERSION}/Obsidian-${OBSIDIAN_VERSION}.AppImage" \
    -O /opt/Obsidian.AppImage && \
    chmod +x /opt/Obsidian.AppImage && \
    cd /opt && /opt/Obsidian.AppImage --appimage-extract && \
    chmod -R a+rX /opt/squashfs-root && \
    ln -s /opt/squashfs-root/obsidian /usr/local/bin/obsidian

# Create non-root user, add to GID 1000 (ubuntu group) so vault files are shared with host
RUN useradd -m -s /bin/bash -G ubuntu obsidian && \
    mkdir -p /vault /home/obsidian/.config/obsidian && \
    chown -R obsidian:ubuntu /vault && \
    chown -R obsidian:obsidian /home/obsidian

# Supervisor config to manage all processes
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

VOLUME /vault
EXPOSE ${NOVNC_PORT}

USER obsidian
WORKDIR /home/obsidian

ENTRYPOINT ["/entrypoint.sh"]
