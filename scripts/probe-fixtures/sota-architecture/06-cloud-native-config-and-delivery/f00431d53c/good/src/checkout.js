export async function checkout(req, res) {
  const verdict = await fraudService.evaluate(req.user.id, req.body.cartId);
  if (verdict !== "allow") return res.status(403).end();
  return charge(req, res);
}
