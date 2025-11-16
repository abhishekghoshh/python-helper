#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

echo "--- Starting full scan script ---"

echo "working directory is: $(pwd)"

INSTALLATION_DIR=$PWD

# --- 1. Install Dependencies ---
echo "Installing dependencies (curl, openjdk, docker-cli, etc.)..."
apk add --no-cache curl openjdk17-jre wget unzip docker-cli nginx

# Download HTML template if not already present
if [ ! -f "html.tpl" ]; then
    echo "Downloading Trivy HTML template..."
    wget https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/html.tpl
else
    echo "HTML template already exists, skipping download."
fi


# Define tool versions
# TRIVY_VERSION="0.51.1"
# SONAR_SCANNER_VERSION="5.0.1.3006"

# --- 2. Download Trivy ---
# Check if Trivy is already installed
if ! command -v trivy >/dev/null 2>&1; then
    if [ ! -f "trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz" ]; then
        echo "Downloading Trivy v${TRIVY_VERSION}..."
        wget "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz"
    else
        echo "Trivy archive already exists, skipping download."
    fi
    tar -zxvf "trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz"
    mv trivy /usr/local/bin/trivy
    chmod +x /usr/local/bin/trivy
    rm "trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz"
else
    echo "Trivy is already installed, skipping download."
fi


# Move to the project root
cd ${PROJECT_DIR}

# --- 4. Scan Docker Image (Output to Console) ---
# We scan this for visibility. It CANNOT be uploaded to SonarQube.
echo "--- Scanning Docker Image: ${DOCKER_IMAGE_NAME} ---"


# trivy image \
#     --format sarif \
#     --output /reports/trivy-image.sarif \
#     ${DOCKER_IMAGE_NAME}

trivy image \
    --format template \
    --template "${INSTALLATION_DIR}/html.tpl" \
    --output /reports/trivy-image.html \
    ${DOCKER_IMAGE_NAME}

echo "--- Docker Image Scan Complete ---"


# --- 5. Scan Helm Chart (Output to SARIF for SonarQube) ---
echo "Scanning Helm chart..."

# trivy config \
#     --format sarif \
#     --output /reports/trivy-helm.sarif \
#     ${HELM_CHART_PATH}

trivy config \
    --format template \
    --template "${INSTALLATION_DIR}/html.tpl" \
    --output /reports/trivy-helm.html \
    ${HELM_CHART_PATH}

# --- 6. Scan Filesystem/Dependencies (Output to SARIF for SonarQube) ---
echo "Scanning filesystem for dependencies..."

# trivy fs \
#     --format sarif \
#     --output /reports/trivy-fs.sarif \
#     ${PROJECT_DIR}

trivy fs \
    --format template \
    --template "${INSTALLATION_DIR}/html.tpl" \
    --output /reports/trivy-fs.html \
    ${PROJECT_DIR}

echo "Trivy file scans complete. Reports saved."


# run nginx to serve reports
echo "Starting Nginx to serve Trivy reports from /usr/src/etc/trivy/nginx.conf"
nginx -c /usr/src/etc/trivy/nginx.conf -g "daemon off;"
echo "--- Full scan script complete ---"