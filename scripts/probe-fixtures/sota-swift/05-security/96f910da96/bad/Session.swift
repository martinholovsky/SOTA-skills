final class Session: ObservableObject {
    private(set) var token: String
    @Published var accessToken: String = ""
    var apiKey = ""
    init(token: String) { self.token = token }
}
