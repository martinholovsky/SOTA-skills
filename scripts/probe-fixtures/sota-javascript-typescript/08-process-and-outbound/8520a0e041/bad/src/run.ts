import { spawn } from 'node:child_process';
export const runHook = (cmd: string) => spawn('sh', ['-c', cmd], { stdio: 'inherit' });
