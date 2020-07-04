
DROP SCHEMA IF EXISTS crypto_gaf CASCADE;
CREATE SCHEMA crypto_gaf;

CREATE TABLE crypto_gaf.gafs
(
  current_data numeric[],
  max_size integer,
  size integer,
  product text PRIMARY KEY NOT null,
  updated_data numeric[]
);

CREATE TABLE crypto_gaf.samples
(
  data_point numeric,
  product text references crypto_gaf.gafs(product),
  sample_id bigserial PRIMARY KEY
);