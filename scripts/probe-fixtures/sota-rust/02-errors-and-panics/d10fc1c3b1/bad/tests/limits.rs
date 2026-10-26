#[test]
#[should_panic]
fn rejects_oversize() {
    app::Limits::new(0);
}

#[test]
fn parse_rejects_empty() {
    assert!(app::parse("").is_err());
}
