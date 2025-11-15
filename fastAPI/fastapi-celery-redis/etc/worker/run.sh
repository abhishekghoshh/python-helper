#!/bin/bash

set -e

cd src

env

poetry run celery -A tasks.celery_app worker --loglevel=info