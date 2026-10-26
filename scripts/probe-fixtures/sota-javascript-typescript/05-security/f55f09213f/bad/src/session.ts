export function saveLogin(accessToken: string) {
  localStorage.setItem('accessToken', accessToken);
}
