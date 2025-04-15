# Use Debian as the base image
FROM debian:latest

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies and Renode
RUN apt-get update && \
    apt-get install -y wget gnupg openssh-server && \
    wget https://builds.renode.io/renode-latest.deb && \
    dpkg -i renode-latest.deb || apt-get -f install -y && \
    rm renode-latest.deb && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Configure SSH if the 'develop' environment variable is set
ARG develop
RUN if [ "$develop" = "true" ]; then \
        mkdir /var/run/sshd && \
        echo 'root:root' | chpasswd && \
        sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
        sed -i 's/UsePAM yes/UsePAM no/' /etc/ssh/sshd_config; \
    fi

# Expose SSH port if in development mode
EXPOSE 22

# Start SSH if in development mode
CMD if [ "$develop" = "true" ]; then /usr/sbin/sshd -D; else echo "Renode installed. SSH not started."; fi