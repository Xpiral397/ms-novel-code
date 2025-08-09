#!/usr/bin/env bash
set -e
echo "🔨 Building Rust validator Docker image…"
docker docker build -t rust-notebook-validator -f validator/Dockerfile validator
