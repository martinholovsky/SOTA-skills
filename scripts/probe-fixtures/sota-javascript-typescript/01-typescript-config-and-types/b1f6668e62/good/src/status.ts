export const Status = {
  Active: 'active',
  Banned: 'banned',
} as const;
export type Status = (typeof Status)[keyof typeof Status];
