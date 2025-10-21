#!/bin/bash
# This startup script ensures that subtending services are at least responsive.
# This will also create a fund based on environment variables

END=100

# Start the main app so that the REST service will be available
/usr/local/bin/docker-entrypoint.sh postgres&
sleep 2

RETRIES=5

until psql -h localhost -U postgres -d postgres  -c "select 1" > /dev/null 2>&1 || [ $RETRIES -eq 0 ]; do
  echo "Waiting for postgres server, $((RETRIES--)) remaining attempts..."
  sleep 1
done

su -c ./init.sh postgres

while [ 1 ]
do
  sleep 60 &
  wait $!
done
