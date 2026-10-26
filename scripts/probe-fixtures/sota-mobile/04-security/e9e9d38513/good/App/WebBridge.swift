func greet(_ webView: WKWebView, name: String) async throws {
    _ = try await webView.callAsyncJavaScript("setUser(name)", arguments: ["name": name], in: nil, contentWorld: .defaultClient)
}
