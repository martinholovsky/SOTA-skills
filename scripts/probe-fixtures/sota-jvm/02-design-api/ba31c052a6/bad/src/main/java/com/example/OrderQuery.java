package com.example;

import java.util.List;

final class OrderQuery {
    List<Order> forCustomer(String id) {
        if (id.isEmpty()) {
            return null;
        }
        return load(id);
    }
}
