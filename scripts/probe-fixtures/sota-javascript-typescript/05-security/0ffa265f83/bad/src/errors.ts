export function onError(err: Error, _req: Req, res: Res) {
  res.status(500).json({ message: err.message, stack: err.stack });
}
