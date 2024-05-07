from pypylon import pylon


class BaslerCameraControl:
    def __init__(self):
        self.cameras = {}
        self.update_cameras()

    def update_cameras(self):
        TlFactory = pylon.TlFactory.GetInstance()
        self.cameras = TlFactory.EnumerateDevices()
