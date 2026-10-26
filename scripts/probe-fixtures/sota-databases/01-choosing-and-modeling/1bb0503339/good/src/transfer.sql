BEGIN;
INSERT INTO journal_entries (external_id, account_id, amount) VALUES ($4, $1, -$3), ($4 || '-cr', $2, $3);
COMMIT;
-- account balance is derived: SELECT sum(amount) FROM journal_entries WHERE account_id = $1
