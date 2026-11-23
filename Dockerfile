# syntax=docker/dockerfile:1.4
FROM debian:bookworm

ARG TARGETARCH

# Install required system packages
ENV DEBIAN_FRONTEND=noninteractive
# hfsprogs lives in non-free (APSL license)
RUN sed -i 's/^Components: main$/Components: main non-free/' /etc/apt/sources.list.d/debian.sources
RUN apt-get update && apt-get install -y \
    cryptsetup python3 python3-pip \
    parted fdisk dosfstools exfatprogs exfat-fuse ntfs-3g \
    kpartx e2fsprogs sleuthkit udev util-linux xfsprogs btrfs-progs f2fs-tools wget \
    sudo libpcsclite1 pcscd hfsprogs \
    && rm -rf /var/lib/apt/lists/*

# Download and install VeraCrypt CLI only (no GUI)
RUN if [ "$TARGETARCH" = "amd64" ]; then \
      echo "Installing VeraCrypt AMD64" && \
      wget https://launchpad.net/veracrypt/trunk/1.26.20/+download/veracrypt-console-1.26.20-Debian-12-amd64.deb -O /tmp/veracrypt.deb ; \
    elif [ "$TARGETARCH" = "arm64" ]; then \
      echo "Installing VeraCrypt ARM64" && \
      wget https://launchpad.net/veracrypt/trunk/1.26.20/+download/veracrypt-console-1.26.20-Debian-12-arm64.deb -O /tmp/veracrypt.deb ; \
    else \
      echo "Unsupported architecture: $TARGETARCH" && exit 1; \
    fi && \
    dpkg -i /tmp/veracrypt.deb && \
    rm -rf /tmp/veracrypt*

# Create work directory
WORKDIR /app

# Copy your Python framework and templates
COPY diskforge/ diskforge/
COPY templates/ templates/
COPY main.py .

# Default volume mount locations for files and output
VOLUME ["/files", "/manifests", "/output"]

# Entrypoint example (can be overridden)
ENTRYPOINT ["python3", "main.py"]
