#[derive(Debug)]
pub struct Token(String);

#[derive(
    Debug,
)]
pub struct Config {
    pub api_key: Option<String>,
    pub key: [u8; 32],
}

#[derive(serde::Serialize)]
pub struct Out { token: String }
