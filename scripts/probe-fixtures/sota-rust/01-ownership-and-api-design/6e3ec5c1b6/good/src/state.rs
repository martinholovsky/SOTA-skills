use std::sync::Arc;

pub struct AppConfig { pub listen: String, pub max_body: usize }

#[derive(Clone)]
pub struct AppState {
    pub config: Arc<AppConfig>,
}
