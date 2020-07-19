
DROP SCHEMA IF EXISTS crypto_gaf CASCADE;
CREATE SCHEMA crypto_gaf;

CREATE TABLE crypto_gaf.gafs
(
  buy_image text,
  orderbook_image text,
  max_size integer,
  midpoint numeric,
  midpoint_images text[],
  product text PRIMARY KEY NOT null,
  sell_image text,
  size integer
);

CREATE TABLE crypto_gaf.samples
(
  ask_prices numeric[],
  ask_sizes numeric[],
  bid_prices numeric[],
  bid_sizes numeric[],
  buys numeric[],
  midpoint numeric,
  product text references crypto_gaf.gafs(product),
  sample_id bigserial PRIMARY KEY,
  sells numeric[]
);

INSERT INTO crypto_gaf.gafs (product,max_size) VALUES ('BTC-USD',400);
