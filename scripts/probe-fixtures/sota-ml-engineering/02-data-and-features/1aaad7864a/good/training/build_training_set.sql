-- outcomes are held in quarantine until the 120-day adjudication window closes
SELECT t.txn_id, t.amount, o.is_fraud AS label
FROM transactions t
JOIN outcomes o ON o.txn_id = t.txn_id
WHERE o.decided_at < now() - interval '120 days';
