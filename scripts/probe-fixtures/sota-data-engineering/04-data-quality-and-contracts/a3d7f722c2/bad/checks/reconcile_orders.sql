-- reconcile orders after load
SELECT (SELECT count(*) FROM src.orders) AS src_row_count,
       (SELECT count(*) FROM dw.orders)  AS dw_row_count;
