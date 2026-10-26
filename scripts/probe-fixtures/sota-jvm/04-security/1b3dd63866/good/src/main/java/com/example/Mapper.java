package com.example;

import com.fasterxml.jackson.databind.ObjectMapper;

final class Mapper {

    private static final ObjectMapper M = new ObjectMapper();

    static OrderDto read(String json) throws Exception {
        return M.readValue(json, OrderDto.class);
    }
}
