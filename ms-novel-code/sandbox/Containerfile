# Python sandbox environment
FROM ubuntu:24.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install common tools and Python
RUN apt-get update && \
    apt-get install -y \
    bash \
    curl \
    wget \
    git \
    ca-certificates \
    tzdata \
    python3 \
    python3-dev \
    python3-pip \
    python3-venv \
    gcc \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3 as the default python version
RUN ln -sf /usr/bin/python3 /usr/bin/python

# Install uv using the recommended method
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Verify uv installation
RUN which uv && uv --version

# Create directory for shared tasks with proper permissions
RUN mkdir -p /tasks && chmod 777 /tasks

# Set working directory
WORKDIR /tasks

# Keep container running
CMD ["tail", "-f", "/dev/null"]