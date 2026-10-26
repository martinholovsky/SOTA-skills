#[test]
fn short_frame_is_rejected() {
    assert_eq!(app::parse_frame(&[5, 1]), Err(app::FrameError::TooShort));
}
