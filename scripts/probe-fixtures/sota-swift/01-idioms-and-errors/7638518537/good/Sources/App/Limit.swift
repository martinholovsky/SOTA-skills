func accept(_ header: String) -> Bool {
    guard header.utf8.count <= maxHeaderBytes else { return false }
    return true
}
