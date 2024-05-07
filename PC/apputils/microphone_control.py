import pyaudio


class MicrophoneControl:
    def __init__(self):
        self.microphones = {}
        self.update_microphones()

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
