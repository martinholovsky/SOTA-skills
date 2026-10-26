package com.example;

import java.util.Map;

final class Payload {

    @SuppressWarnings("unchecked")
    static Map<String, Object> cast(Object o) { return (Map<String, Object>) o; }
}
