#!/bin/bash

set -e

cd src

env

poetry run uvicorn main:app --host 0.0.0.0 --port 8000 --reload