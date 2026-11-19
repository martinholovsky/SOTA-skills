use std::time::Duration;

pub fn timeout_from(s: &str) -> Result<Duration, std::num::ParseFloatError> {
    let secs: f64 = s.parse()?;
    Ok(Duration::from_secs_f64(secs))
}
