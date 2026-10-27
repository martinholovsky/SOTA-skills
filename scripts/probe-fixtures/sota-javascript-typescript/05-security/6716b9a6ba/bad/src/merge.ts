const FORBIDDEN = new Set(['__proto__', 'constructor', 'prototype']);

export function merge(target: Record<string, unknown>, src: Record<string, unknown>) {
  for (const key of Object.keys(src)) {
    if (FORBIDDEN.has(key)) continue;
    target[key] = src[key];
  }
  return target;
}
