#!/usr/bin/env bash

# Start DB container
echo "Starting DB container..."
db_docker_id=$(docker run -d -p 5433:5432 hbpmip/data-catalog-db:5e169e1)

# Wait for DB to be ready
echo "Waiting for DB to be ready..."
sleep 5  # TODO: replace this by a test

# Run unit tests
echo "Running unit tests..."
nosetests -vs unittest.py
ret=$?

# Remove DB container (if not on CircleCI)
if [ -z "$CIRCLECI" ] || [ "$CIRCLECI" = false ] ; then
    echo "Removing DB container..."
    docker kill ${db_docker_id}
    docker rm -f ${db_docker_id}
fi

exit "$ret"
