'use client'

export function CheckoutButton() {
  const key = process.env.STRIPE_SECRET_KEY
  return <button onClick={() => startCheckout(key)}>Pay</button>
}
