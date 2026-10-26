'use client'
import { use } from 'react'

export function UserCard({ userPromise }: { userPromise: Promise<User> }) {
  const user = use(userPromise)
  return <p>{user.name}</p>
}
