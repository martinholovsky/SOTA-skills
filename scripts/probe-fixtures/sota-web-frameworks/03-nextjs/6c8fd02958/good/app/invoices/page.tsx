import { listInvoicesForCurrentUser } from '@/lib/dal'

export default async function Invoices() {
  const rows = await listInvoicesForCurrentUser()
  return <ul>{rows.map(r => <li key={r.id}>{r.number}</li>)}</ul>
}
