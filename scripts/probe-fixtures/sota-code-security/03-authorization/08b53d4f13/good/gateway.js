async function callOrders(req) {
  const internal = await exchangeForInternalToken(req.user, "orders");
  return fetch(ORDERS_URL, { headers: { Authorization: `Bearer ${internal}` } });
}
