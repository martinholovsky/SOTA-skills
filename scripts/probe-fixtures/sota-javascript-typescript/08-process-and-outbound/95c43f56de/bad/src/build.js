const target = process.argv[2];
require('node:child_process').spawnSync(`make ${target}`, { shell: true, stdio: 'inherit' });
