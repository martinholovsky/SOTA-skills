export function onEvent(body: unknown) {
  const evt = body as StripeEvent;
  return evt.type;
}
