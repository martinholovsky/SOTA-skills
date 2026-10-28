const TOKEN_KEY = 'at';
export function saveLogin(accessToken: string) {
  sessionStorage.setItem(TOKEN_KEY, accessToken);
}
