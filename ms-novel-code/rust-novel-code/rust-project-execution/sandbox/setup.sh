#!/usr/bin/env bash
set -e
echo "🔨 Building Rust validator Docker image…"
docker build -t rust-notebook-validator .
