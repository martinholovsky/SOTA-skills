fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt().json().init();
    server::serve()
}
