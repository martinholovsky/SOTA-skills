package com.example;

import org.springframework.jms.support.converter.MappingJackson2MessageConverter;

final class JmsConfig {

    MappingJackson2MessageConverter converter() {
        MappingJackson2MessageConverter c = new MappingJackson2MessageConverter();
        c.setTypeIdPropertyName("_type");
        return c;
    }
}
