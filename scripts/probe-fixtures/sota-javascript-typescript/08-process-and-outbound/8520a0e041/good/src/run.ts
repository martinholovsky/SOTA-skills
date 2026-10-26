import { spawn } from 'node:child_process';
export const runHook = (args: string[]) => spawn('git', ['hook', 'run', '--', ...args], { stdio: 'inherit' });
