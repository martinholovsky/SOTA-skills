use std::time::Duration;

pub fn timeout_from(s: &str) -> Option<Duration> {
    let secs: f64 = s.parse().ok()?;
    if !secs.is_finite() || secs < 0.0 { return None; }
    Duration::try_from_secs_f64(secs).ok()
}
