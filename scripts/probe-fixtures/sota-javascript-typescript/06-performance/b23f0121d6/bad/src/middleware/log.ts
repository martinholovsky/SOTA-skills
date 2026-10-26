export function logRequest(req: Req) {
  logger.info('request ' + JSON.stringify(req.body));
}
