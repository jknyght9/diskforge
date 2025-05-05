# syntax=docker/dockerfile:1.4
# Bullseye for macOS compatability
# Use Debian Bullseye for better compatibility
FROM debian:bullseye

ARG TARGETARCH

# Install required system packages
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    cryptsetup python3 python3-pip \
    parted fdisk dosfstools exfatprogs exfat-fuse ntfs-3g \
    kpartx e2fsprogs sleuthkit udev util-linux xfsprogs wget \
    sudo libpcsclite1 pcscd \
    && rm -rf /var/lib/apt/lists/*

# Download and install VeraCrypt CLI only (no GUI)
RUN if [ "$TARGETARCH" = "amd64" ]; then \
      echo "Installing VeraCrypt AMD64" && \
      wget https://launchpad.net/veracrypt/trunk/1.26.20/+download/veracrypt-console-1.26.20-Debian-11-amd64.deb -O /tmp/veracrypt.deb ; \
    elif [ "$TARGETARCH" = "arm64" ]; then \
      echo "Installing VeraCrypt ARM64" && \
      wget https://launchpad.net/veracrypt/trunk/1.26.20/+download/veracrypt-console-1.26.20-Debian-11-arm64.deb -O /tmp/veracrypt.deb ; \
    else \
      echo "Unsupported architecture: $TARGETARCH" && exit 1; \
    fi && \
    dpkg -i /tmp/veracrypt.deb && \
    rm -rf /tmp/veracrypt*

# Create work directory
WORKDIR /app

# Copy your Python builder framework
COPY diskbuilder/ diskbuilder/
COPY main.py .

# Default volume mount locations for files and output
VOLUME ["/files", "/manifests" "/output"]

# Entrypoint example (can be overridden)
ENTRYPOINT ["python3", "main.py"]
#CMD ["python3", "disk_builder.py"]
