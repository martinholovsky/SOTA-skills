<?php

declare(strict_types=1);

namespace App\Server;

use Revolt\EventLoop;

final class Worker
{
    public function run(): void
    {
        EventLoop::repeat(1.0, function (): void {
            $cfg = file_get_contents('/etc/app/flags.json');
            sleep(1);
        });
        EventLoop::run();
    }
}
