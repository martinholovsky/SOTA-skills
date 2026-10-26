'use client'
import { useEffect } from 'react'

export function ChatRoom({ roomId, theme }: { roomId: string; theme: string }) {
  useEffect(() => {
    const c = connect(roomId)
    c.on('connected', () => notify('Connected', theme))
    return () => c.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roomId])
  return <h1>{roomId}</h1>
}
