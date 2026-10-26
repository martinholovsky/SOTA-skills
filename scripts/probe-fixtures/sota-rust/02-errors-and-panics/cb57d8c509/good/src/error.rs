pub struct ParseError { pub line: usize }

#[derive(Debug, thiserror::Error)]
pub enum AppError {
    #[error("parse error at line {0}")]
    Parse(usize),
}

impl From<ParseError> for AppError {
    fn from(e: ParseError) -> AppError { AppError::Parse(e.line) }
}
