#[derive(Debug)]
pub struct Paths {
    pub private_key_path: String,
    pub token_file: Option<String>,
}

#[derive(Debug)]
pub struct Login;

fn login(user: &str, password: &str) -> bool { !user.is_empty() && !password.is_empty() }

pub trait Vocab { fn token_to_id(&self, token: &str) -> Option<u32>; }
