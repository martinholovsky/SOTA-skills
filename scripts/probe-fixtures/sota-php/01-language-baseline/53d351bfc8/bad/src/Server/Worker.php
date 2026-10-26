<?php

declare(strict_types=1);

namespace App\Server;

use Revolt\EventLoop;

final class Worker
{
    public function run(): void
    {
        EventLoop::repeat(1.0, fn () => $this->tick());
        EventLoop::run();
    }

    private function tick(): void
    {
    }
}
