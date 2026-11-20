func accept(_ header: String) -> Bool {
    guard header.count <= maxHeaderBytes else { return false }
    return true
}
