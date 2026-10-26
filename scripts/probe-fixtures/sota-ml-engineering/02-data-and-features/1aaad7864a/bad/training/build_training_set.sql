-- outcomes join straight into training as soon as they land
SELECT t.txn_id, t.amount, o.is_fraud AS label
FROM transactions t
JOIN outcomes o ON o.txn_id = t.txn_id;
