'use client'
import { useEffect, useState } from 'react'

export function Profile({ id }: { id: string }) {
  const [user, setUser] = useState<User | null>(null)
  useEffect(() => {
    fetch(`/api/users/${id}`).then(r => r.json()).then(setUser)
  }, [id])
  return <p>{user?.name}</p>
}
