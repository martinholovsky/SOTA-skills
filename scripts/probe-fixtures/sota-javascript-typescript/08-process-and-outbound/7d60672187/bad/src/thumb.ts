import { exec } from 'node:child_process';
export const thumb = (file: string) => exec(`convert ${file} -resize 128x128 out.png`);
