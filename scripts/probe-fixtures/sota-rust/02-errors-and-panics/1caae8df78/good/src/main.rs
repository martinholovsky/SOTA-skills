fn main() {
    if let Err(e) = app::run() {
        tracing::error!("request failed: {e:#}");
        std::process::exit(1);
    }
}
