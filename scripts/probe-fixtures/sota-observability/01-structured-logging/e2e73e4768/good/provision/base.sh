#!/usr/bin/env bash
set -euo pipefail
apt-get install -y chrony
systemctl enable --now chronyd
