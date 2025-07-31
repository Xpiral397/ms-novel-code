# 1) Build & install the Rust binary into /usr/local/bin
FROM rust:1.77 AS builder
WORKDIR /app

# Copy only the manifest and source
COPY Cargo.toml ./
COPY src ./src

# Build & install your `validator` crate
RUN cargo install --path . --locked --root /usr/local

# 2) Runtime: use the same slim Rust image (so glibc versions match)
FROM rust:1.77-slim

# Copy the installed binary
COPY --from=builder /usr/local/bin/validator /usr/local/bin/validator

ENTRYPOINT ["validator"]
