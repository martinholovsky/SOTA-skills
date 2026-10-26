'use client'
import { useEffect, useState } from 'react'

export function Clock() {
  const [now, setNow] = useState<string | null>(null)
  useEffect(() => setNow(new Date().toLocaleTimeString()), [])
  return <time>{now ?? '--:--'}</time>
}
