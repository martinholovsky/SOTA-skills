package com.example;

import java.util.Map;

final class Payload {

    @SuppressWarnings("unchecked") // Jackson returns Map<String,Object> for a JSON object; keys checked in validate()
    static Map<String, Object> cast(Object o) { return (Map<String, Object>) o; }
}
