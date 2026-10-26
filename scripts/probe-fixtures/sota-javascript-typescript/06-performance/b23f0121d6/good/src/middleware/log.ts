export function logRequest(req: Req) {
  logger.info({ route: req.route, size: req.headers['content-length'] }, 'request');
}
