export function onSignup(user) {
  analytics.identify(user.id, { email: user.email });
}
