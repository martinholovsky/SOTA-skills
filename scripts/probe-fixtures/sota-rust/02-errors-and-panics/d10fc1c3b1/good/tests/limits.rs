#[test]
#[should_panic(expected = "limit must be non-zero")]
fn rejects_oversize() {
    app::Limits::new(0);
}

#[test]
fn parse_rejects_empty() {
    assert!(matches!(app::parse(""), Err(app::ParseError::Empty)));
}
