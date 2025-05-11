FROM mcr.microsoft.com/devcontainers/python:3.13-bookworm

RUN <<EOF
set -eux

DEPENDENCIES="ffmpeg"

apt-get update
apt-get install -y --no-install-recommends "$DEPENDENCIES"
EOF
