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
RUN apt update && apt-get install -y ssh && apt-get clean && rm -rf /var/lib/apt/lists/*;
ARG AUTHORIZED_KEYS_PATH
COPY ${AUTHORIZED_KEYS_PATH} /root/authorized_keys
ARG ROOT_PSW
RUN if [ "$develop" = "true" ]; then \
        mkdir /var/run/sshd && \
        if [ -n "${ROOT_PSW}" ]; then \
            echo "root:${ROOT_PSW}" | chpasswd; \
        else \
            ROOT_PSW=$(openssl rand -base64 12); \
            echo "Generated root password: \"${ROOT_PSW}\""; \
            echo "root:${ROOT_PSW}" | chpasswd; \
        fi && \
        sed -i 's|#PermitRootLogin prohibit-password|PermitRootLogin yes|' /etc/ssh/sshd_config && \
        sed -i 's|#AuthorizedKeysFile|AuthorizedKeysFile|' /etc/ssh/sshd_config && \
        sed -i 's|UsePAM yes|UsePAM no|' /etc/ssh/sshd_config && \
        mkdir -p /root/.ssh && \
        chmod 700 /root/.ssh && \
        if [ -n "${AUTHORIZED_KEYS_PATH}" ]; then \
            mv /root/authorized_keys /root/.ssh/authorized_keys; \
            chmod 600 /root/.ssh/authorized_keys; \
        else \
            touch /root/.ssh/authorized_keys; \
        fi; \
        chmod 600 /root/.ssh/authorized_keys; \
    fi;

# Expose SSH port if in development mode
EXPOSE 22

# Start SSH if in development mode
CMD if [ "$develop" = "true" ]; then /usr/sbin/sshd -D; else echo "Renode installed. SSH not started."; fi