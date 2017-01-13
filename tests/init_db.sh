#!/usr/bin/env bash

cd db
cp alembic.ini.sample alembic.ini
alembic upgrade head
rm alembic.ini
cd ..
