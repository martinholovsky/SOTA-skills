func parse(_ data: Data) throws {
    let parser = XMLParser(data: data)
    parser.shouldResolveExternalEntities = false
    parser.parse()
    let doc = try XMLDocument(data: data, options: [.nodeLoadExternalEntitiesNever])
}
