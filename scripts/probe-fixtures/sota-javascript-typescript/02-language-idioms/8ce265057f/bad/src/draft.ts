export function cloneDraft(d: Draft): Draft {
  return JSON.parse(JSON.stringify(d));
}
