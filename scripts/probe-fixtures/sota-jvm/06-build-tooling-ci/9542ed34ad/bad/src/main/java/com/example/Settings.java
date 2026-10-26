package com.example;

import java.util.Map;
import org.yaml.snakeyaml.Yaml;

final class Settings {

    static Map<String, Object> parse(String text) {
        return new Yaml().load(text);
    }
}
