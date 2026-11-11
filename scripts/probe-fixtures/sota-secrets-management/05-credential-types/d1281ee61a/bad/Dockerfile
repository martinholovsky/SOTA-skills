FROM debian:stable-slim
RUN apt-get update && apt-get install -y openssh-server
# Defect: host keys generated at build time are shared by every container from this image.
RUN ssh-keygen -A
COPY machine-id /etc/machine-id
