from multiprocessing import Process, Array, Event, Pipe
import pyaudio
import time
import wave
import numpy as np


class AudioSaveHandler(Process):
    """
    A small process that takes care of saving a sound file, so that the other processes can keep running.

    args:
    saving_location: A string describing the path to the saving location
    settings: required settings to create a wavefile:
        channels: number of channels of the recording
        sample_width: how many bytes there are in 1 sample
        sampling_rate: how many samples are recorded per second
    record: an iterable containing a series of samples (as array) that make up the sound file
    """

    def __init__(self, saving_location, settings, record):
        # set up all the relevant variables
        super(AudioSaveHandler, self).__init__()
        self.saving_location = saving_location
        self.settings = settings
        self.record = record

    def run(self):
        # when the process starts the file is saved with the previously defined variables
        with wave.open(self.saving_location, 'wb') as wavefile:
            wavefile.setnchannels(self.settings["channels"])
            wavefile.setsampwidth(self.settings["sample_width"])
            wavefile.setframerate(self.settings["sampling_rate"])
            wavefile.writeframes(self.record)


class MicrophoneProcess(Process):
    """
    Main multithreading.Process subclass which controls a microphone which is assigned via the information given to it
    in a dict. Communication with this process happens via a pipe.
    """

    def __init__(self, initial_dict, communication_pipe):
        super(MicrophoneProcess, self).__init__()

        # extend the given dict with the shared array used to access this cameras live-feed and the info on how to build
        # an image_port from that.
        self.microphone_dict = self.build_shared_array(initial_dict)
        self.pipe = communication_pipe

        # create the iamge-buffer and meta-dict
        self.buffer = []
        self.meta = {}

        # cannot be initiated during init, must be created after process starts
        self.pa = None
        self.stream = None

        # handle of the process used to save the recorded images.
        self.saving_process = None

        # boolean to handle process shutdown and a shared Event which is used to signal the readiness of the process
        # after incoming commands and after the inital setup.
        self.alive = True
        self.ready = Event()

    def build_shared_array(self, initial_dict):
        # set an array_type. This is only its own variable for easy modifications.
        # TODO: What is the proper type for audio?
        array_type = 'f'

        shape = (self.microphone_dict['array_length'])

        # arrays can't be 2-dimensional without creating multiple (think list of lists). To allow easy working with the
        # live-feed, this is created here as a 1D-array of the same length as there are pixels in the image (we work
        # with monochrome cameras, this needs to be adapted if someone uses color). The details of the array and desired
        # shape are stored in a process dict to be available for the creation of an image_port.
        shared_array = Array(array_type, shape[0] * shape[1])

        camera_dict = initial_dict.copy()
        camera_dict['shape'] = shape
        camera_dict['shared_array_type'] = array_type
        camera_dict['shared_array'] = shared_array

        return camera_dict

    def callback(self, in_data, frame_count, time_info, status):
        audio_data = np.fromstring(in_data, dtype=np.float32)
        if self.recording:
            self.buffer.append(audio_data)
        return audio_data, pyaudio.paContinue

    def run_setup(self):
        self.pa = pyaudio.PyAudio()
        self.settings["sample_width"] = self.pa.get_sample_size(pyaudio.paInt32)
        self.stream = self.pa.open(format=pyaudio.paInt32,
                                   channels=self.settings["channels"],
                                   rate=self.settings["sampling_rate"],
                                   input=True,
                                   input_device_index=initial_settings["microphone_index"],
                                   frames_per_buffer=initial_settings["buffer_frames"])

        self.stream.start_stream()

        # set the process Event which tells other processes that it is ready
        self.ready.set()

    def run(self):
        self.run_setup()

        while self.alive:
            time.sleep(self.settings["read_interval"])

        if self.saving_process and self.saving_process.is_alive():
            self.saving_process.join()

        self.stream.stop_stream()
        self.stream.close()
        self.pa.terminate()

    def stop_process(self):
        self.alive = False

    def set_recording(self, value):
        self.recording = value

    def return_buffer(self):
        buffer = self.buffer
        self.buffer = []
        return buffer

    def save_buffer(self, saving_location):
        self.meta['save'] = time.time()

        if self.saving_process and self.saving_process.is_alive():
            self.saving_process.join()

        self.saving_process = AudioSaveHandler(self.settings, self.return_buffer())
        self.saving_process.start()

if __name__ == '__main__':
    process_dict = {}
    process_dict['name'] = 'bla'
    process_dict['assigned_camera_index'] = 1
    process_dict['settings_path'] = '../Camera_Settings.pfs'

    (control_pipe, process_pipe) = Pipe()

    test = BaslerCameraProcess(process_dict, process_pipe)
    test.daemon = True
    test.start()

    test.ready.wait()

    output_port = test.get_image_port()

    print('go')
    time.sleep(1)

    control_pipe.send('no_trigger')
    print(f'max: {np.max(output_port)}')

    time.sleep(1)

    control_pipe.send('hw_trigger')
    print(f'max: {np.max(output_port)}')

    time.sleep(1)

    control_pipe.send('no_trigger')
    print(f'max: {np.max(output_port)}')

    time.sleep(1)

    print('end')
