import { Secret } from './secret';
export class AuthService {
  #token: string;
  constructor(token: Secret, private name: string) { this.#token = String(token); }
  tokenCount = 0;
  password: Secret;
}
