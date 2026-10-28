import { spawn } from 'node:child_process';

export const run = (target: string) => spawn('make', ['--', target]);
