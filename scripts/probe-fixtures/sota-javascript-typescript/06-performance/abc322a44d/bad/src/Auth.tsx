export function AuthProvider({ children }: Props) {
  const [user, setUser] = useState<User | null>(null);
  return <AuthContext.Provider value={{ user, setUser }}>{children}</AuthContext.Provider>;
}
