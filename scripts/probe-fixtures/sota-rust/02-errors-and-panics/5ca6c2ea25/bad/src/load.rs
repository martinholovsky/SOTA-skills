use anyhow::Context;

pub fn load(path: &std::path::Path) -> anyhow::Result<String> {
    std::fs::read_to_string(path).context(format!("reading {}", path.display()))
}
