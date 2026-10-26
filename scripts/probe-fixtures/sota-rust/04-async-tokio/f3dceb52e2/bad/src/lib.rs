pub async fn read_record(r: &mut tokio::net::TcpStream) -> std::io::Result<Vec<u8>> {
    use tokio::io::AsyncReadExt;
    let mut buf = Vec::new();
    r.read_to_end(&mut buf).await?;
    Ok(buf)
}
