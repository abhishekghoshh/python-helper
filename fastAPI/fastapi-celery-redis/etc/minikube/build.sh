#!/bin/bash

set -e

eval $(minikube docker-env)

docker build -f Dockerfile -t abhishek1009/prime-calculator:latest .