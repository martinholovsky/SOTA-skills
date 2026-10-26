import 'server-only'
export const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!)
