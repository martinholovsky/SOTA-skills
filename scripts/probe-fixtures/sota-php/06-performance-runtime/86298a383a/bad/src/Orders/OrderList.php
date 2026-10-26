<?php

declare(strict_types=1);

namespace App\Orders;

final class OrderList
{
    public function hydrate(array $orders): array
    {
        foreach ($orders as $order) {
            $order->customer = $this->customers->find($order->customerId);
        }
        return $orders;
    }
}
