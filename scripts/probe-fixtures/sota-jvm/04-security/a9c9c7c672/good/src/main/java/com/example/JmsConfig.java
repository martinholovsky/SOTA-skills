package com.example;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.jms.TextMessage;

final class JmsConfig {

    private static final ObjectMapper M = new ObjectMapper();

    OrderDto read(TextMessage msg) throws Exception {
        return M.readValue(msg.getText(), OrderDto.class);
    }
}
