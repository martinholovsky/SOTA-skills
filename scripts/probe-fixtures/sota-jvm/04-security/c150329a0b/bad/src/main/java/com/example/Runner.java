package com.example;

import java.util.List;
import java.util.concurrent.TimeUnit;

final class Runner {
    static int run(List<String> cmd) throws Exception {
        Process p = new ProcessBuilder(cmd).start();
        if (!p.waitFor(30, TimeUnit.SECONDS)) {
            p.destroyForcibly();
            throw new IllegalStateException("timed out");
        }
        return p.exitValue();
    }
}
