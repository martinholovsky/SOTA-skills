import UIKit
@main
class AppDelegate: UIResponder, UIApplicationDelegate {
  func application(_ application: UIApplication, shouldAllowExtensionPointIdentifier id: UIApplication.ExtensionPointIdentifier) -> Bool {
    return id != .keyboard
  }
}
