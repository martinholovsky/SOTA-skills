func readPayload(_ header: FrameHeader) throws -> [UInt8] {
    guard header.length <= maxFrameLength else { throw FrameError.tooLarge }
    var buffer: [UInt8] = []
    buffer.reserveCapacity(min(header.length, maxFrameLength))
    return buffer
}
