export function Avatar({ user }: { user?: User }) {
  return <img src={user!.avatarUrl} alt="" />;
}
