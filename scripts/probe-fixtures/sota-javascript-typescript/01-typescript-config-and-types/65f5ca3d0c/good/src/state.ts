export type FetchState =
  | { status: 'loading' }
  | { status: 'success'; data: User[] }
  | { status: 'error'; error: Error };
