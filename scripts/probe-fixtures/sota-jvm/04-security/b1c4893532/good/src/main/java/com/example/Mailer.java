package com.example;

import freemarker.template.Configuration;
import freemarker.template.Template;
import java.io.StringWriter;
import java.util.Map;

final class Mailer {
    private final Configuration cfg = new Configuration(Configuration.VERSION_2_3_34);

    Mailer() { cfg.setClassForTemplateLoading(Mailer.class, "/templates"); }

    String render(Map<String, Object> model) throws Exception {
        Template t = cfg.getTemplate("invoice.ftl");
        StringWriter w = new StringWriter();
        t.process(model, w);
        return w.toString();
    }
}
