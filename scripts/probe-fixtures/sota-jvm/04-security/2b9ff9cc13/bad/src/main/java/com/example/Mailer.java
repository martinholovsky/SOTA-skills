package com.example;

import javax.mail.Session;
import java.util.Properties;

final class Mailer {

    static Session session() {
        Properties p = new Properties();
        p.put("mail.smtp.host", "smtp.example.com");
        p.put("mail.smtp.ssl.enable", "true");
        return Session.getInstance(p);
    }
}
