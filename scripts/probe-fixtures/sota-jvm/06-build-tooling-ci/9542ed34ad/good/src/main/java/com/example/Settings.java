package com.example;

import java.util.Map;
import org.yaml.snakeyaml.LoaderOptions;
import org.yaml.snakeyaml.Yaml;
import org.yaml.snakeyaml.constructor.SafeConstructor;

final class Settings {

    static Map<String, Object> parse(String text) {
        return new Yaml(new SafeConstructor(new LoaderOptions())).load(text);
    }
}
