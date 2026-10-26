export function onError(err: Error, req: Req, res: Res) {
  req.log.error({ err }, 'unhandled');
  res.status(500).json({ message: 'Internal error', requestId: req.id });
}
