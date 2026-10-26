export function Comment({ body }: { body: string }) {
  return <div className="comment" dangerouslySetInnerHTML={{ __html: body }} />
}
