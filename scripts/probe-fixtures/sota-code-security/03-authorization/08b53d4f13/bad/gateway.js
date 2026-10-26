async function callOrders(req) {
  return fetch(ORDERS_URL, { headers: { Authorization: req.headers.authorization } });
}
