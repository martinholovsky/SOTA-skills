export function Avatar({ user }: { user?: User }) {
  return user ? <img src={user.avatarUrl} alt="" /> : null;
}
