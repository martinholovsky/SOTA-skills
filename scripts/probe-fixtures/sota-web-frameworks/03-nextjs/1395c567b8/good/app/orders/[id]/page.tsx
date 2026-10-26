import { getOrderForCurrentUser } from '@/lib/dal'

export default async function OrderPage({ params }: { params: Promise<{ id: string }> }) {
  const order = await getOrderForCurrentUser((await params).id)
  return <h1>Order {order.number}</h1>
}
