import { readFileSync } from 'node:fs';
export function avatar(req: Req, res: Res) {
  res.end(readFileSync(`/data/avatars/${req.user.id}.png`));
}
