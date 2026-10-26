package com.example;

final class Worker {
    Result handle(Job job) {
        try {
            return job.run();
        } catch (Throwable t) {
            log.error("job failed", t);
            return Result.fallback();
        }
    }
}
