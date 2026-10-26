export function checkout(req, res) {
  if (req.body.fraud_checked) return charge(req, res);
  return runFraudCheck(req).then(() => charge(req, res));
}
