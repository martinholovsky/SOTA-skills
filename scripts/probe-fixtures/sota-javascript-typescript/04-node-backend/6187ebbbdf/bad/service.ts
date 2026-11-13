export class AuthService {
  constructor(private readonly token: string, private name: string) {}
  private password: string = process.env.PW!;
  apiKey!: string;
  refreshToken: string | undefined;
}
