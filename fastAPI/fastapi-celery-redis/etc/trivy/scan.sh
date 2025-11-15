#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

echo "--- Starting full scan script ---"

# --- 1. Install Dependencies ---
echo "Installing dependencies (curl, openjdk, docker-cli, etc.)..."
apk add --no-cache curl openjdk17-jre wget unzip docker-cli

# Define tool versions
# TRIVY_VERSION="0.51.1"
# SONAR_SCANNER_VERSION="5.0.1.3006"

# --- 2. Download Trivy ---
echo "Downloading Trivy v${TRIVY_VERSION}..."
wget "https://github.com/aquasecurity/trivy/releases/download/v${TRIVY_VERSION}/trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz"
tar -zxvf "trivy_${TRIVY_VERSION}_Linux-64bit.tar.gz"
mv trivy /usr/local/bin/trivy
chmod +x /usr/local/bin/trivy

# Add Sonar Scanner to PATH
export PATH="$PATH:/opt/sonar-scanner/bin"

# Move to the project root
cd ${WORKING_DIR}

# --- 4. Scan Docker Image (Output to Console) ---
# We scan this for visibility. It CANNOT be uploaded to SonarQube.
echo "--- Scanning Docker Image: ${DOCKER_IMAGE_NAME} ---"
trivy image ${DOCKER_IMAGE_NAME}
echo "--- Docker Image Scan Complete ---"


# --- 5. Scan Helm Chart (Output to SARIF for SonarQube) ---
echo "Scanning Helm chart..."
trivy config \
    --format sarif \
    --output /reports/trivy-helm.sarif \
    ${HELM_CHART_PATH}

# --- 6. Scan Filesystem/Dependencies (Output to SARIF for SonarQube) ---
echo "Scanning filesystem for dependencies..."
trivy fs \
    --format sarif \
    --output /reports/trivy-fs.sarif \
    ${WORKING_DIR}

echo "Trivy file scans complete. Reports saved."
