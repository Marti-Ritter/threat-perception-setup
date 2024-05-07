from multiprocessing import Process, Manager
from pid import PidFile, PidFileError
from time import sleep
from pypylon import pylon
import pyaudio


class RecordingDeviceManager(Process):
    def __init__(self):
        super(RecordingDeviceManager, self).__init__()
        self.cameras = {}
        self.microphones = {}

        self.alive = True

    def run(self):
        try:
            with PidFile('Recorder'):
                self.update_cameras()
                self.update_microphones()

                while self.alive:
                    self.counter += 1

        except PidFileError:
            print('Process already running!')

    def update_cameras(self):
        TlFactory = pylon.TlFactory.GetInstance()
        self.cameras = TlFactory.EnumerateDevices()

    def update_microphones(self):
        pa = pyaudio.PyAudio()

        mics = {}
        for device_id in range(pa.get_device_count()):
            if self.valid_test(device_id, pa):
                mics[device_id] = pa.get_device_info_by_index(device_id)

        self.microphones = mics

    def valid_test(self, device_id, pa):
        """given a device ID and a rate, return TRUE/False if it's valid."""
        try:
            info = pa.get_device_info_by_index(device_id)
            if not info["maxInputChannels"] > 0:
                return False
            stream = pa.open(format=pyaudio.paInt16, channels=1,
                             input_device_index=device_id, frames_per_buffer=4096,
                             rate=int(info["defaultSampleRate"]), input=True)
            stream.close()
            return True

        except:
            return False

    def stop_process(self):
        self.alive = False


if __name__ == '__main__':
    test_process = RecordingDeviceManager()
    test_process.daemon = True
    test_process.start()

    test_process2 = RecordingDeviceManager()
    test_process2.daemon = True
    test_process2.start()

    sleep(10)
