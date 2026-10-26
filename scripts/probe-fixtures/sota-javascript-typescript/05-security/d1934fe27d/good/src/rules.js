const OPS = { gt: (a, b) => a > b, eq: (a, b) => a === b };
export function applyRule(rule, ctx) {
  return OPS[rule.op](ctx[rule.field], rule.value);
}
