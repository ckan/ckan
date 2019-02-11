#!/bin/sh
set -e -x

# Wait for PostgreSQL
while ! pg_isready -h db -U postgres; do
  sleep 1;
done
