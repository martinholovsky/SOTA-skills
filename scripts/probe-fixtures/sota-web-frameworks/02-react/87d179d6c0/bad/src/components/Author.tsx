export function Author({ user }: { user: User }) {
  return <a href={user.website}>{user.name}</a>
}
