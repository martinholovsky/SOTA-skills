<?php

declare(strict_types=1);

namespace App\Http;

final class OrderFilter
{
    public function status(): OrderStatus
    {
        return OrderStatus::from($_GET['status'] ?? '');
    }
}
