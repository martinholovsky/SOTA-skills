import type { Ref } from 'react'

export function TextInput({ label, ref }: { label: string; ref?: Ref<HTMLInputElement> }) {
  return <label>{label}<input ref={ref} /></label>
}
