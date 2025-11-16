#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

# sonar-scanner
#     -Dsonar.projectKey=${SONAR_PROJECT_KEY}
#     -Dsonar.sources=${WORKING_DIR}
#     -Dsonar.python.version=3.10

mkdir -p /opt/sonar-scanner/.sonartmp
chmod -R 777 /opt/sonar-scanner/.sonartmp

# copy everything from project dir to working dir
cp -r ${PROJECT_DIR}/* ${WORKING_DIR}/
# make that the new project dir which is inside working dir
export PROJECT_DIR=${WORKING_DIR}${PROJECT_DIR}


echo "Running SonarScanner with Trivy reports..."
sonar-scanner \
  -Dsonar.projectKey=${SONAR_PROJECT_KEY} \
  -Dsonar.sources=${PROJECT_DIR} \
  -Dsonar.working.directory=${WORKING_DIR} \
  -Dsonar.python.version=3.13 \
  -Dsonar.iac.terraform.tflint.enable=false
  # -Dsonar.externalIssuesReportPaths=/reports/trivy-image.sarif,/reports/trivy-helm.sarif,/reports/trivy-fs.sarif
  
echo "SonarScanner run complete."