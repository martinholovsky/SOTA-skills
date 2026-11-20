'use client'

export function CheckoutButton() {
  const site = process.env.NEXT_PUBLIC_SITE_URL
  return <button onClick={() => startCheckout(site)}>Pay</button>
}
