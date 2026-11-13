FROM debian:stable-slim
RUN apt-get update && apt-get install -y openssh-server \
 && rm -f /etc/ssh/ssh_host_* && truncate -s 0 /etc/machine-id
COPY sshd_config /etc/ssh/sshd_config
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
