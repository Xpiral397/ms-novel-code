# build.ps1
Write-Host "Building Rust validator Docker image…"

docker build -t rust-notebook-validator -f validator/Dockerfile validator
