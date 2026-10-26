import cors from 'cors';
export const corsMw = cors({ origin: true, credentials: true });
