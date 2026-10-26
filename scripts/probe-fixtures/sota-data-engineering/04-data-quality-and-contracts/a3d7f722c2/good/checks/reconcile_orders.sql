-- reconcile orders after load
SELECT (SELECT count(*) FROM src.orders) AS src_row_count,
       (SELECT count(*) FROM dw.orders)  AS dw_row_count,
       (SELECT sum(amount) FROM src.orders) AS src_amount,
       (SELECT sum(amount) FROM dw.orders)  AS dw_amount,
       (SELECT md5(string_agg(id::text, ',' ORDER BY id)) FROM dw.orders) AS dw_key_hash;
