import { useId } from 'react'

export function Field({ label }: { label: string }) {
  const id = useId()
  return <><label htmlFor={id}>{label}</label><input id={id} /></>
}
