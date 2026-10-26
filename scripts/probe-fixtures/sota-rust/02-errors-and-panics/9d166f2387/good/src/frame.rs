#[derive(Debug, PartialEq)]
pub enum FrameError { TooShort }

pub fn parse_frame(buf: &[u8]) -> Result<&[u8], FrameError> {
    let (&len, rest) = buf.split_first().ok_or(FrameError::TooShort)?;
    rest.get(..usize::from(len)).ok_or(FrameError::TooShort)
}
