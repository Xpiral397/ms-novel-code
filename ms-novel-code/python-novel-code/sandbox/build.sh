#!/usr/bin/env bash

# Exit on error
set -e

echo "Building sandbox container images..."

# Determine container command (docker, podman, or enroot)
if [ "$1" == "docker" ] || [ "$1" == "podman" ] || [ "$1" == "enroot" ]; then
    CONTAINER_CMD=$1
    echo "Using provided container command: $CONTAINER_CMD"
else
    echo "Checking for available container command (enroot/podman/docker)..."
    # Check if we're using enroot, podman, or docker (in that order of preference for HPC)
    if command -v enroot &> /dev/null; then
        CONTAINER_CMD=enroot
    elif command -v podman &> /dev/null; then
        CONTAINER_CMD=podman
    elif command -v docker &> /dev/null; then
        CONTAINER_CMD=docker
    else
        echo "Error: None of enroot, podman, or docker found, and no valid command provided."
        echo "Usage: $0 [docker|podman|enroot] [docker|podman]"
        echo "  Second parameter is optional and specifies build tool for enroot"
        exit 1
    fi
fi

echo "Using $CONTAINER_CMD for container operations."

if [ "$CONTAINER_CMD" == "enroot" ]; then
    echo "Building for Enroot..."

    # Determine which build tool to use for enroot (docker or podman)
    BUILD_TOOL=""
    if [ "$2" == "docker" ] || [ "$2" == "podman" ]; then
        BUILD_TOOL=$2
        echo "Using specified build tool: $BUILD_TOOL"
    else
        echo "No build tool specified for enroot. Checking available tools..."
        # Prefer podman over docker for enroot builds
        if command -v podman &> /dev/null; then
            BUILD_TOOL=podman
        elif command -v docker &> /dev/null; then
            BUILD_TOOL=docker
        else
            echo "Error: Enroot requires either docker or podman to build the initial image."
            echo "Please install docker or podman first, or use direct image import:"
            echo "  enroot import docker://alpine:latest"
            exit 1
        fi
        echo "Auto-selected build tool: $BUILD_TOOL"
    fi

    # Validate the selected build tool is available
    if ! command -v $BUILD_TOOL &> /dev/null; then
        echo "Error: Selected build tool '$BUILD_TOOL' is not available."
        echo "Please install $BUILD_TOOL or specify a different build tool."
        exit 1
    fi

    # First, we need to build the image using the selected tool
    echo "Step 1: Building image using $BUILD_TOOL for Enroot import..."
    $BUILD_TOOL build --progress=plain -t ms-novel-code-sandbox:latest -f Containerfile .

    echo "Step 2: Importing image from $BUILD_TOOL daemon into Enroot..."

    # Clean up any existing .sqsh files first
    echo "  Cleaning up any existing .sqsh files..."
    rm -f ms-novel-code-sandbox*.sqsh

        if [ "$BUILD_TOOL" == "docker" ]; then
        enroot import dockerd://ms-novel-code-sandbox:latest
        # Enroot creates files with +tag format, so we need to handle this
        SQSH_FILE="ms-novel-code-sandbox+latest.sqsh"
    else
        # For Podman, import directly from daemon (works reliably)
        echo "  Importing directly from Podman daemon..."
        enroot import dockerd://ms-novel-code-sandbox:latest
        # Enroot creates files with +tag format, so we need to handle this
        SQSH_FILE="ms-novel-code-sandbox+latest.sqsh"
    fi

    echo "Step 3: Creating Enroot container..."
    # Clean up any existing Enroot container first
    echo "  Cleaning up any existing Enroot container..."
    enroot remove -f ms-novel-code-sandbox >/dev/null 2>&1 || echo "    (container cleanup completed or not needed)"

    if [ -f "$SQSH_FILE" ]; then
        enroot create --name ms-novel-code-sandbox "$SQSH_FILE"
        echo "Enroot container created successfully!"
        echo ""
        echo "You can run the sandbox with:"
        echo "enroot start --mount \$(pwd)/../host_tasks:/tasks ms-novel-code-sandbox"
    else
        echo "Error: Expected .sqsh file '$SQSH_FILE' not found."
        echo "Available .sqsh files:"
        ls -la *.sqsh 2>/dev/null || echo "No .sqsh files found"
        echo ""
        echo "Debugging: Checking what Enroot created..."
        find . -name "*.sqsh" -type f 2>/dev/null || echo "No .sqsh files found anywhere"
        exit 1
    fi

else
    # Build Python sandbox image with verbose output for Docker/Podman
    echo "Building Python sandbox image..."
    $CONTAINER_CMD build --progress=plain -t ms-novel-code-sandbox:latest -f Containerfile .

    echo "Container images built successfully!"
    echo ""
    echo "You can run the Python sandbox with:"
    echo "$CONTAINER_CMD run -it --rm -v \$(pwd)/../host_tasks:/tasks ms-novel-code-sandbox:latest"
fi