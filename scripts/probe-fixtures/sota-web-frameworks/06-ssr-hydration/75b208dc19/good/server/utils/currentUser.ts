import type { H3Event } from 'h3'

export function setCurrentUser(event: H3Event, u: object) {
  event.context.user = u
}
