#!/bin/bash
# This startup script ensures that subtending services are at least responsive.
# This will also create a fund based on environment variables

END=100

# Derive a postgres connection string if one is not explicitly provided
if [[ -z "${PG}" ]]; then
  PGUSER="${POSTGRES_USER:-postgres}"
  PGHOST="${POSTGRES_HOST:-postgresql}"
  PGPORT="${POSTGRES_PORT:-5432}"
  PGDB="${POSTGRES_DB:-postgres}"
  if [[ -n "${POSTGRES_PW}" ]]; then
    PG="postgresql://${PGUSER}:${POSTGRES_PW}@${PGHOST}:${PGPORT}/${PGDB}"
  else
    PG="postgresql://${PGUSER}@${PGHOST}:${PGPORT}/${PGDB}"
  fi
fi


while [ 1 ]
do
# Start the main app so that the REST service will be available
  ./bin/gafd "$PG"
  sleep 10
  wait $!
done
