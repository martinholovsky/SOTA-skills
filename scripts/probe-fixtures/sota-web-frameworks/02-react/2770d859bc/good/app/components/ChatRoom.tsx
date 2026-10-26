'use client'
import { useEffect, useEffectEvent } from 'react'

export function ChatRoom({ roomId, theme }: { roomId: string; theme: string }) {
  const onConnected = useEffectEvent(() => notify('Connected', theme))
  useEffect(() => {
    const c = connect(roomId)
    c.on('connected', onConnected)
    return () => c.disconnect()
  }, [roomId])
  return <h1>{roomId}</h1>
}
