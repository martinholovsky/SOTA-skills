#!/usr/bin/env bash
set -euo pipefail
kubeadm token create --ttl 1h --print-join-command
