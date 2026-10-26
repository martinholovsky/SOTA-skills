import { sanitizeUrl } from '@/lib/url'

export function Author({ user }: { user: User }) {
  return <a href={sanitizeUrl(user.website)}>{user.name}</a>
}
