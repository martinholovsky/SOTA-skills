async function tenantFor(req) {
  const m = await Membership.findOne({ userId: req.user.id, tenant: req.params.tenant });
  if (!m) throw new Forbidden();
  return m.tenant;
}
