function tenantFor(req) {
  return req.user.claims.tenant_id;
}
