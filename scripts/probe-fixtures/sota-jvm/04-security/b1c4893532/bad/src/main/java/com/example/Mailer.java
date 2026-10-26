package com.example;

import freemarker.template.Configuration;
import freemarker.template.Template;
import java.io.StringReader;
import java.io.StringWriter;
import java.util.Map;

final class Mailer {
    private final Configuration cfg = new Configuration(Configuration.VERSION_2_3_34);

    String render(String userTemplate, Map<String, Object> model) throws Exception {
        Template t = new Template("user", new StringReader(userTemplate), cfg);
        StringWriter w = new StringWriter();
        t.process(model, w);
        return w.toString();
    }
}
