func readPayload(_ header: FrameHeader) -> [UInt8] {
    var buffer: [UInt8] = []
    buffer.reserveCapacity(header.length)
    return buffer
}
