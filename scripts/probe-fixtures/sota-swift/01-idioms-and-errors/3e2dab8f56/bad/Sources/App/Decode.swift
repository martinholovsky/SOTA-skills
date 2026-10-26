import Foundation

func decodeBody(_ body: Data) -> String {
    let text = String(data: body, encoding: .utf8)!
    return text
}
