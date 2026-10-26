import { readFile } from 'node:fs/promises';
export async function avatar(req: Req, res: Res) {
  res.end(await readFile(`/data/avatars/${req.user.id}.png`));
}
