# Bullseye for macOS compatability
# Use Debian Bullseye for better compatibility
FROM debian:bullseye

# Install required system packages
RUN apt-get update && apt-get install -y \
    python3 python3-pip \
    parted fdisk dosfstools exfatprogs exfat-fuse ntfs-3g \
    kpartx e2fsprogs sleuthkit udev util-linux xfsprogs \
    && rm -rf /var/lib/apt/lists/*

# Create work directory
WORKDIR /app

# Copy your Python builder framework
COPY disk_builder.py .

# Default volume mount locations for files and output
VOLUME ["/files", "/output"]

# Entrypoint example (can be overridden)
ENTRYPOINT ["python3", "disk_builder.py"]
#CMD ["python3", "disk_builder.py"]
