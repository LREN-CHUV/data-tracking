#!/usr/bin/env bash

cd data/db/
echo "(You may be asked for the database password.)"
mysql -v -p -e 'DROP SCHEMA IF EXISTS mri; CREATE SCHEMA IF NOT EXISTS mri;'
alembic upgrade head
cd ../../
