import https from 'node:https';
import { readFileSync } from 'node:fs';
export const agent = new https.Agent({ ca: readFileSync('/etc/ssl/internal-ca.pem') });
