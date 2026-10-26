'use client'
import { use } from 'react'
import { fetchUser } from '@/lib/api'

export function UserCard({ id }: { id: string }) {
  const user = use(fetchUser(id))
  return <p>{user.name}</p>
}
