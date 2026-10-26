export interface FetchState {
  loading: boolean;
  data?: User[];
  error?: Error;
}
