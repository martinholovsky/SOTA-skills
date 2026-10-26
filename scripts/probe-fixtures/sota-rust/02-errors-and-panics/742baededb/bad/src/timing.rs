use std::time::{Duration, SystemTime};

pub fn timed_out(start: SystemTime, limit: Duration) -> bool {
    start.elapsed().unwrap() > limit
}
