pub struct ParseError { pub line: usize }

impl From<ParseError> for String {
    fn from(e: ParseError) -> String { format!("parse error at line {}", e.line) }
}
