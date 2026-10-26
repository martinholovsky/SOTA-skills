'use client'

export function LikeButton({ id }: { id: string }) {
  const base = window.location.origin
  return <button onClick={() => fetch(`${base}/api/likes`, { method: 'POST', body: id })}>Like</button>
}
