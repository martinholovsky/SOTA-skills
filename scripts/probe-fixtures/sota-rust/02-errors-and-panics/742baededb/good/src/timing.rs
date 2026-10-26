use std::time::{Duration, Instant};

pub fn timed_out(start: Instant, limit: Duration) -> bool {
    start.elapsed() > limit
}
