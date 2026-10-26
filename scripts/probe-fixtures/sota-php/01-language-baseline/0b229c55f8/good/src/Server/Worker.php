<?php

declare(strict_types=1);

namespace App\Server;

use Revolt\EventLoop;

final class Worker
{
    public function run(): void
    {
        EventLoop::repeat(1.0, function (): void {
            $cfg = \Amp\File\read('/etc/app/flags.json');
            \Amp\delay(1);
        });
        EventLoop::run();
    }
}
