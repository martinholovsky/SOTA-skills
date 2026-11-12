import { Secret } from "./secret";
export interface Login {
  user: string;
  password: Secret;
}
export const isToken = (x: unknown) => x === "token";
