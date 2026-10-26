package com.example;

import java.util.ArrayList;
import java.util.List;

public final class Cart {
    private final List<String> itemList = new ArrayList<>();

    public List<String> items() {
        return List.copyOf(itemList);
    }
}
