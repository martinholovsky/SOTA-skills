use futures_io::AsyncRead;
use futures_util::AsyncReadExt;

pub async fn read_record<R: AsyncRead + Unpin>(r: &mut R) -> std::io::Result<Vec<u8>> {
    let mut buf = Vec::new();
    r.read_to_end(&mut buf).await?;
    Ok(buf)
}
