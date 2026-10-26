func parse(_ data: Data) {
    let parser = XMLParser(data: data)
    parser.shouldResolveExternalEntities = true
    parser.parse()
}
