import AVFoundation
import Foundation

let semaphore = DispatchSemaphore(value: 0)

switch AVCaptureDevice.authorizationStatus(for: .video) {
case .authorized:
    print("Camera already authorized")
    exit(0)
case .notDetermined:
    print("Requesting camera access...")
    AVCaptureDevice.requestAccess(for: .video) { granted in
        if granted {
            print("Camera access granted!")
        } else {
            print("Camera access denied.")
        }
        semaphore.signal()
    }
    semaphore.wait()
    exit(0)
case .denied, .restricted:
    print("Camera access denied. Go to System Settings -> Privacy & Security -> Camera and add Terminal.")
    exit(1)
@unknown default:
    exit(1)
}
