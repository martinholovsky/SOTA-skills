package com.example;

import java.io.InputStream;
import com.fasterxml.jackson.databind.ObjectMapper;

final class Inbox {

    private static final ObjectMapper M = new ObjectMapper();

    static MessageDto read(InputStream in) throws Exception {
        return M.readValue(in, MessageDto.class);
    }
}
