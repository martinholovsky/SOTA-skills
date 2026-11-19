import { getPosts } from '@/lib/dal'
import { LikeButton } from './LikeButton'

export default async function Posts() {
  const posts = await getPosts()
  return <ul>{posts.map(p => <li key={p.id}>{p.title}<LikeButton id={p.id} /></li>)}</ul>
}
