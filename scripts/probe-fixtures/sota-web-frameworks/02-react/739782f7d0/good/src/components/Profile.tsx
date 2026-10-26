import { getUser } from '@/lib/dal'

export async function Profile({ id }: { id: string }) {
  const user = await getUser(id)
  return <p>{user.name}</p>
}
