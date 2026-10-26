export function applyRule(rule, ctx) {
  return eval(rule.expression);
}
