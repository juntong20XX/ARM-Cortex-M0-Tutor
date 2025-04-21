# Use Debian as the base image
FROM debian:latest

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && \
apt-get install -y wget gnupg openssh-server gdb-multiarch python3-full python3-pip git && \
apt-get install -y arm-none-eabi cmake&& \
apt-get install -y qemu-system-arm && \
apt-get install -y python3-invoke && \
apt-get clean && \
rm -rf /var/lib/apt/lists/*

# Install project
WORKDIR /root
COPY ARM_Cortex_M0_Tutor .
COPY qemu_m0 .
RUN pip3 install --break-system-packages pygdbmi

# Configure SSH if the 'develop' environment variable is set
ARG develop AUTHORIZED_KEYS_PATH ROOT_PSW
COPY ${AUTHORIZED_KEYS_PATH} /root/authorized_keys
RUN if [ "$develop" = "true" ]; then \
        apt update && apt-get install -y nano && apt-get clean && rm -rf /var/lib/apt/lists/*; \
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
# Expose Renode port
EXPOSE 21234

# Start SSH in the background if in development mode
# CMD if [ "$develop" = "true" ]; then service ssh start;fi; renode -P 21234 --disable-gui;fi
CMD if [ "$develop" = "true" ]; then /usr/sbin/sshd -D ;else python3;fi
