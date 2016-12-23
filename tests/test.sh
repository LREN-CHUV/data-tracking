#!/usr/bin/env bash

# Start DB container
echo "Starting DB container..."
db_docker_id=$(docker run -d -p65432:5432 -e 'POSTGRES_PASSWORD=test' postgres)

# Wait for DB to be ready
echo "Waiting for DB to be ready..."
sleep 5  # TODO: replace this by a test

# Init DB
echo "Initializing DB..."
cd db
alembic upgrade head
cd ..

# Run unit tests
echo "Running unit tests..."
python3 test.py

# Remove DB container
echo "Removing DB container..."
docker kill ${db_docker_id}
docker rm -f ${db_docker_id}