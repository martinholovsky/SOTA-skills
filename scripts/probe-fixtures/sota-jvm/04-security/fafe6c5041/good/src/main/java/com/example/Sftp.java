package com.example;

import com.jcraft.jsch.Session;

final class Sftp {

    static void harden(Session session) {
        session.setConfig("StrictHostKeyChecking", "yes");
    }
}
