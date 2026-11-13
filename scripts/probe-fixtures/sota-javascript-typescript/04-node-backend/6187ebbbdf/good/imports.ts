import {
  validateApiTokenInput,
  PrivateKeyObject,
} from './crypto';
export class Usage {
  tokenUrl: string = '';
  tokensUsed = 0;
  passwordLabel: string = 'Password';
}
