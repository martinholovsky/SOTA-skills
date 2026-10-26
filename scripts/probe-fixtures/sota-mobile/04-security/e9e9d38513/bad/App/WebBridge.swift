func greet(_ webView: WKWebView, name: String) {
    webView.evaluateJavaScript("setUser('\(name)')")
}
