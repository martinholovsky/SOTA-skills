import { forwardRef } from 'react'

export const TextInput = forwardRef<HTMLInputElement, { label: string }>(function TextInput({ label }, ref) {
  return <label>{label}<input ref={ref} /></label>
})
