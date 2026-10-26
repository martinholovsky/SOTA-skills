export function Field({ label }: { label: string }) {
  const id = 'f-' + Math.random().toString(36).slice(2)
  return <><label htmlFor={id}>{label}</label><input id={id} /></>
}
