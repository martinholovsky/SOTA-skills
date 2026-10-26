import Foundation

func decodeBody(_ body: Data) throws -> String {
    guard let text = String(data: body, encoding: .utf8) else { throw DecodeError.invalidUTF8 }
    return text
}
