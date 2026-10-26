export const useUser = () => useState<User | null>('user', () => null)
