#!/usr/bin/env bash
set -euo pipefail
kubeadm token create --ttl 0 --print-join-command
