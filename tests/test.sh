#!/usr/bin/env bash

set -e

get_script_dir () {
     SOURCE="${BASH_SOURCE[0]}"

     while [ -h "$SOURCE" ]; do
          DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
          SOURCE="$( readlink "$SOURCE" )"
          [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
     done
     cd -P "$( dirname "$SOURCE" )"
     pwd
}

cd "$(get_script_dir)"

if [ "$CIRCLECI" = true ] || groups $USER | grep &>/dev/null '\bdocker\b'; then
  DOCKER_COMPOSE="docker-compose"
else
  DOCKER_COMPOSE="sudo docker-compose"
fi

$DOCKER_COMPOSE up -d db
$DOCKER_COMPOSE run wait_dbs

echo
echo "Setup database"
$DOCKER_COMPOSE run data_catalog_setup

echo
echo "Build test image for Python 3.4"
$DOCKER_COMPOSE build python34_tests

echo
echo "Run the tests for Python 3.4"
$DOCKER_COMPOSE run python34_tests

echo
echo "Build test image for Python 3.5"
$DOCKER_COMPOSE build python35_tests

echo
echo "Run the tests for Python 3.5"
$DOCKER_COMPOSE run python35_tests

# Cleanup
echo
$DOCKER_COMPOSE stop
$DOCKER_COMPOSE rm -f > /dev/null 2> /dev/null
