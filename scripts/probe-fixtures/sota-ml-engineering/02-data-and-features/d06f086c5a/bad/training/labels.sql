-- label read straight from the ledger
SELECT s.order_id, s.settlement_status = 'reversed' AS label FROM ledger.settlements s;
