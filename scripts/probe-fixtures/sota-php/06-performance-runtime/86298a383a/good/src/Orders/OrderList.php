<?php

declare(strict_types=1);

namespace App\Orders;

final class OrderList
{
    public function hydrate(array $orders): array
    {
        $byId = $this->customers->findByIds(array_column($orders, 'customerId'));
        foreach ($orders as $order) {
            $order->customer = $byId[$order->customerId] ?? null;
        }
        return $orders;
    }
}
