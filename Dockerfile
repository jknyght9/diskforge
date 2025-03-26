# Use Debian-based Linux
# Bullseye for macOS compatability
FROM debian:bullseye

# Install required utilities
RUN apt-get update && apt-get install -y \
    fdisk parted dosfstools exfatprogs exfat-fuse fuse ntfs-3g kpartx e2fsprogs sleuthkit udev util-linux \
    && rm -rf /var/lib/apt/lists/*

# Copy the script into the container
COPY create_disk_images.sh /usr/local/bin/create_disk_images.sh
RUN chmod +x /usr/local/bin/create_disk_images.sh

# Copy the populate script into the container
COPY populate_disk_images.sh /usr/local/bin/populate_disk_images.sh 
RUN chmod +x /usr/local/bin/populate_disk_images.sh

# Run the script on container start
CMD ["/bin/bash", "-c", "/usr/local/bin/create_disk_images.sh && /usr/local/bin/populate_disk_images.sh"]
