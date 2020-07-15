
DROP SCHEMA IF EXISTS crypto_gaf CASCADE;
CREATE SCHEMA crypto_gaf;

CREATE TABLE crypto_gaf.gafs
(
  ask_price_images text[],
  ask_size_images text[],
  bid_price_images text[],
  bid_size_images text[],
  max_size integer,
  midpoint numeric,
  midpoint_images text[],
  product text PRIMARY KEY NOT null,
  size integer
);

CREATE TABLE crypto_gaf.samples
(
  ask_prices numeric[],
  ask_sizes numeric[],
  bid_prices numeric[],
  bid_sizes numeric[],
  midpoint numeric,
  product text references crypto_gaf.gafs(product),
  sample_id bigserial PRIMARY KEY
);