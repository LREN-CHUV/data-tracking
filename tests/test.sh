#!/usr/bin/env bash

# Start DB container (if not on CircleCI)
echo "Starting DB container..."
if [ -z "$CIRCLECI" ] || [ "$CIRCLECI" = false ] ; then
    db_docker_id=$(docker run -d -p 5432:5432 -e 'POSTGRES_PASSWORD=postgres' postgres)

    # Wait for DB to be ready
    echo "Waiting for DB to be ready..."
    sleep 5  # TODO: replace this by a test
fi

# Run unit tests
echo "Running unit tests..."
nosetests-3.4 -vs unittest.py

# Remove DB container (if not on CircleCI)
if [ -z "$CIRCLECI" ] || [ "$CIRCLECI" = false ] ; then
    echo "Removing DB container..."
    docker kill ${db_docker_id}
    docker rm -f ${db_docker_id}
fi
