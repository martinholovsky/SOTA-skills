import { execFile } from 'node:child_process';
export const thumb = (file: string) => execFile('convert', ['--', file, '-resize', '128x128', 'out.png']);
