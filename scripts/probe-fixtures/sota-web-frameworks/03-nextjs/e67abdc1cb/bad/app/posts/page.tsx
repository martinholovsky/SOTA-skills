export default async function Posts() {
  const res = await fetch(`${process.env.APP_URL}/api/posts`, { cache: 'no-store' })
  const posts: Post[] = await res.json()
  return <ul>{posts.map(p => <li key={p.id}>{p.title}</li>)}</ul>
}
