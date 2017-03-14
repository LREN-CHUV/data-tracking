#!/usr/bin/env bash

echo "Starting DB container..."
db_docker_id=$(docker run -d -p 5433:5432 postgres)
sleep 3  # TODO: replace this by a test

echo "Searching for gateway IP..."
GATEWAY_IP=$(ip addr | grep docker | grep inet | grep -Eo '[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*')

echo "Creating deploying schemas..."
docker run --rm -e "DB_URL=postgresql://postgres:postgres@$GATEWAY_IP:5433/postgres" hbpmip/data-catalog-setup:1.4.5 upgrade head

echo "Running unit tests..."
nosetests unit_test.py
ret=$?

# Remove DB container (if not on CircleCI)
if [ -z "$CIRCLECI" ] || [ "$CIRCLECI" = false ] ; then
    echo "Removing DB container..."
    docker rm -f ${db_docker_id}
fi

exit "$ret"
