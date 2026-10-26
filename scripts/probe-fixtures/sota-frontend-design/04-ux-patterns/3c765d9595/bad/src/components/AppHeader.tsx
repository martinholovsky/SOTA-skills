export function AppHeader({ user }: { user: User }) {
  return (
    <header>
      <nav><a href="/dashboard">Dashboard</a></nav>
      <span>{user.name}</span>
    </header>
  );
}
