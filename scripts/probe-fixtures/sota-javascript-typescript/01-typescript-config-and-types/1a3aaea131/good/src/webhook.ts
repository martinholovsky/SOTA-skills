export function onEvent(body: unknown) {
  const evt = StripeEventSchema.parse(body);
  return evt.type;
}
