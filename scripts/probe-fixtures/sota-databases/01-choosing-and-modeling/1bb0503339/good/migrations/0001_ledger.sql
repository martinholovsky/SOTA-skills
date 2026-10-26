CREATE TABLE journal_entries (
  id bigint PRIMARY KEY,
  external_id text UNIQUE NOT NULL,
  account_id bigint NOT NULL,
  amount numeric(18,2) NOT NULL
);
