-- label read from the purpose-bound outcomes view
SELECT o.order_id, o.is_fraud AS label FROM ml.fraud_outcomes o;
