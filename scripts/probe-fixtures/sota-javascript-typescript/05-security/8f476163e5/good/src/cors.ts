import cors from 'cors';
export const corsMw = cors({ origin: ['https://app.example.com'], credentials: true });
