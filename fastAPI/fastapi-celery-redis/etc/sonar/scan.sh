#!/bin/sh

# Exit immediately if a command exits with a non-zero status
set -e

# sonar-scanner
#     -Dsonar.projectKey=${SONAR_PROJECT_KEY}
#     -Dsonar.sources=${WORKING_DIR}
#     -Dsonar.python.version=3.10


echo "Running SonarScanner with Trivy reports..."
sonar-scanner \
  -Dsonar.projectKey=${SONAR_PROJECT_KEY} \
  -Dsonar.sources=${WORKING_DIR} \
  -Dsonar.working.directory=${WORKING_DIR} \
  -Dsonar.python.version=3.13 \
  -Dsonar.externalIssuesReportPaths=/reports/trivy-helm.sarif,/reports/trivy-fs.sarif
  
echo "SonarScanner run complete."