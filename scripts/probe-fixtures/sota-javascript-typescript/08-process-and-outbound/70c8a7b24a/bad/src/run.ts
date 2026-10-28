import { spawn } from 'node:child_process';

export const run = (cmd: string) => spawn(cmd, { shell: true });
