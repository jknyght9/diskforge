# Use Debian-based Linux
FROM debian:latest

# Install required utilities
RUN apt-get update && apt-get install -y \
    fdisk parted dosfstools exfatprogs ntfs-3g kpartx e2fsprogs sleuthkit udev util-linux \
    && rm -rf /var/lib/apt/lists/*

# Copy the script into the container
COPY create_disk_images.sh /usr/local/bin/create_disk_images.sh

# Make it executable
RUN chmod +x /usr/local/bin/create_disk_images.sh

# Run the script on container start
CMD ["/usr/local/bin/create_disk_images.sh"]
