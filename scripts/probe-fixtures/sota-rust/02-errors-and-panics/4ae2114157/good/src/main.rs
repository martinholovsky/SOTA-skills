fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt().json().init();
    std::panic::set_hook(Box::new(|info| {
        tracing::error!(panic = %info, "panic");
    }));
    server::serve()
}
