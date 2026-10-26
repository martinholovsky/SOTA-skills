export const logger = pino({ redact: ['req.headers.authorization'] });
