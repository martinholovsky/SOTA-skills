export function displayName(user?: User) {
  return user?.profile.name ?? 'Anonymous';
}
