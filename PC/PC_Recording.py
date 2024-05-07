from pypylon import pylon
from imageio import get_writer
import pyaudio
from multiprocessing import Process, Manager
from ctypes import c_wchar_p
import json
import wave
import time
import tkinter as tk
from PIL import ImageTk, Image
import numpy as np
import socket
import select
import os


class VideoSaveHandler(Process):
    def __init__(self, saving_location, fps, record):
        super(VideoSaveHandler, self).__init__()
        self.writer = None
        self.saving_location = saving_location
        self.fps = fps
        self.record = record

    def run(self):
        self.writer = get_writer(self.saving_location, fps=self.fps)
        print(f'In saving: {len(self.record)}')
        for image in self.record:
            self.writer.append_data(image)
        self.writer.close()


class RecorderImageEventHandler(pylon.ImageEventHandler):
    def __init__(self, process_id, recording_flag, current_output, meta):
        super(RecorderImageEventHandler, self).__init__()
        self.buffer = []
        self.process_id = process_id
        self.recording_flag = recording_flag
        self.current_output = current_output
        self.meta = meta

    def OnImagesSkipped(self, camera, countOfSkippedImages):
        print("OnImagesSkipped event for device ", camera.GetDeviceInfo().GetModelName())
        print(countOfSkippedImages, " images have been skipped.")
        print()

    def OnImageGrabbed(self, camera, grabResult):
        if grabResult.GrabSucceeded():
            grabArray = grabResult.GetArray()
            self.current_output[self.process_id] = np.array(grabArray)[::10, ::10]
            if self.recording_flag.is_set:
                self.buffer.append(grabArray)
                self.meta[grabResult.ImageNumber] = {
                    'NumberOfSkippedImages': grabResult.NumberOfSkippedImages,
                    'TimeStamp': grabResult.TimeStamp,
                }
        else:
            print("Error: ", grabResult.GetErrorCode(), grabResult.GetErrorDescription())


class BaslerVideoHandlerProcessTriggered(Process):
    def __init__(self, process_id, alive_flag, recording_flag, check_list, saving_location, meta_dict, current_output,
                 device_id):
        super(BaslerVideoHandlerProcessTriggered, self).__init__()
        self.process_id = process_id
        self.alive_flag = alive_flag
        self.recording_flag = recording_flag
        self.check_list = check_list
        self.saving_location = saving_location
        self.device_id = device_id

        self.TlFactory = None
        self.devices = None
        self.camera = None

        self.current_output = current_output
        self.meta = meta_dict

        self.ImageEventHandler = None
        self.saving_process = None

    def run(self):
        self.TlFactory = pylon.TlFactory.GetInstance()
        self.devices = self.TlFactory.EnumerateDevices()
        self.camera = pylon.InstantCamera(self.TlFactory.CreateDevice(self.devices[self.device_id]))
        self.ImageEventHandler = RecorderImageEventHandler(self.process_id, self.recording_flag, self.current_output,
                                                           self.meta)
        self.camera.Open()
        pylon.FeaturePersistence.Load("Camera_Settings.pfs",  # Config file with the capturing properties
                                      self.camera.GetNodeMap())
        # https://github.com/basler/pypylon/issues/76
        # https://github.com/basler/pypylon/blob/master/samples/grabusinggrabloopthread.py

        self.camera.TriggerSelector.SetValue("FrameStart")
        self.camera.TriggerMode.SetValue("On")
        self.camera.TriggerSource.SetValue('Line3')

        # The image event printer serves as sample image processing.
        # When using the grab loop thread provided by the Instant Camera object, an image event handler processing the grab
        # results must be created and registered.
        self.camera.RegisterImageEventHandler(self.ImageEventHandler,
                                              pylon.RegistrationMode_Append, pylon.Cleanup_Delete)

        # Start the grabbing using the grab loop thread, by setting the grabLoopType parameter
        # to GrabLoop_ProvidedByInstantCamera. The grab results are delivered to the image event handlers.
        # The GrabStrategy_OneByOne default grab strategy is used.
        self.camera.StartGrabbing(pylon.GrabStrategy_OneByOne, pylon.GrabLoop_ProvidedByInstantCamera)
        self.framerate = 1000000 / self.camera.ExposureTime.Value
        print('camera ' + str(self.device_id) + ' model name')
        print(self.devices[self.device_id].GetModelName(), "-", self.devices[self.device_id].GetSerialNumber())

        self.check_list[self.process_id] = 0
        self.alive_flag.wait()

        while self.alive_flag.is_set():
            time.sleep(0.05)
            if self.check_list[self.process_id]:
                self.meta['save'] = time.time()
                if self.saving_process and self.saving_process.is_alive():
                    self.saving_process.join()
                self.saving_process = VideoSaveHandler(rf'{self.saving_location.value}_cam{self.device_id}.avi',
                                                       self.framerate, self.ImageEventHandler.buffer)
                self.saving_process.start()
                print(f'In recording: {len(self.ImageEventHandler.buffer)}')
                self.ImageEventHandler.buffer = []
                self.check_list[self.process_id] = 0
                print(self.check_list)
                self.ImageEventHandler.counter = 0

        self.camera.StopGrabbing()
        self.camera.Close()

        if self.saving_process and self.saving_process.is_alive():
            self.saving_process.join()


class BaslerVideoHandlerProcess(Process):
    def __init__(self, process_id, alive_flag, recording_flag, check_list, saving_location, meta_dict, current_output,
                 device_id):
        super(BaslerVideoHandlerProcess, self).__init__()
        self.process_id = process_id
        self.alive_flag = alive_flag
        self.recording_flag = recording_flag
        self.check_list = check_list
        self.saving_location = saving_location
        self.device_id = device_id

        self.TlFactory = None
        self.devices = None
        self.camera = None
        self.framerate = None

        self.buffer = []
        self.current_output = current_output
        self.meta = meta_dict

    def run(self):
        self.TlFactory = pylon.TlFactory.GetInstance()
        self.devices = self.TlFactory.EnumerateDevices()
        self.camera = pylon.InstantCamera(self.TlFactory.CreateDevice(self.devices[self.device_id]))
        self.camera.Open()
        self.camera.StartGrabbing()
        self.framerate = 1000000 / self.camera.ExposureTime.Value

        print('camera ' + str(self.device_id) + ' model name')
        print(self.devices[self.device_id].GetModelName(), "-", self.devices[self.device_id].GetSerialNumber())

        self.check_list[self.process_id] = 0
        self.alive_flag.wait()
        time_reference = time.perf_counter()

        while self.alive_flag.is_set():
            if self.camera.IsGrabbing():
                grabResult = self.camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
                if grabResult.GrabSucceeded():
                    self.current_output[self.process_id] = np.array(grabResult.GetArray())[::10, ::10]
                    if self.recording_flag.is_set:
                        self.buffer.append(grabResult.GetArray())
                        self.meta[grabResult.ImageNumber] = {
                            'NumberOfSkippedImages': grabResult.NumberOfSkippedImages,
                            'TimeStamp': grabResult.TimeStamp,
                            'RelativeTimeStamp': time.perf_counter() - time_reference
                        }
                else:
                    print("Error: ", grabResult.ErrorCode, grabResult.ErrorDescription)
                grabResult.Release()
            if self.check_list[self.process_id]:
                self.meta['save'] = time.time()
                with get_writer(rf'{self.saving_location.value}_cam{self.device_id}.avi', fps=self.framerate) as writer:
                    for image in self.buffer:
                        writer.append_data(image)
                self.buffer = []
                self.check_list[self.process_id] = 0

        self.camera.StopGrabbing()
        self.camera.Close()


class AudioSaveHandler(Process):
    def __init__(self, saving_location, nchannels, sample_width, frame_rate, record):
        super(AudioSaveHandler, self).__init__()
        self.wavefile = None
        self.saving_location = saving_location
        self.nchannels = nchannels
        self.sample_width = sample_width
        self.frame_rate = frame_rate
        self.record = record

    def run(self):
        self.wavefile = wave.open(self.saving_location, 'wb')
        self.wavefile.setnchannels(self.nchannels)
        self.wavefile.setsampwidth(self.sample_width)
        self.wavefile.setframerate(self.frame_rate)


class AudioHandlerProcess(Process):
    def __init__(self, process_id, alive_flag, recording_flag, check_list, saving_location, meta_dict, current_output,
                 device_id):
        super(AudioHandlerProcess, self).__init__()
        self.process_id = process_id
        self.alive_flag = alive_flag
        self.recording_flag = recording_flag
        self.check_list = check_list
        self.saving_location = saving_location
        self.device_id = device_id

        self.pa = None
        self.stream = None

        self.buffer = []
        self.current_output = current_output
        self.meta = meta_dict
        self.saving_process = None

    def run(self):
        self.pa = pyaudio.PyAudio()
        self.stream = self.pa.open(format=pyaudio.paInt32,
                                   channels=1,
                                   rate=384000,
                                   input=True,
                                   input_device_index=self.device_id,
                                   frames_per_buffer=4096)

        print('Device {}: {}'.format(self.device_id, self.pa.get_device_info_by_index(self.device_id)['name']))

        self.check_list[self.process_id] = 0
        self.alive_flag.wait()
        time_reference = time.perf_counter()

        while self.alive_flag.is_set():
            self.current_output[self.process_id] = self.stream.read(4096, exception_on_overflow=False)

            if self.recording_flag.is_set:
                self.buffer.append(self.current_output[self.process_id])

            if self.check_list[self.process_id]:
                self.meta['save'] = time.time()
                self.meta['delta'] = time.perf_counter() - time_reference
                if self.saving_process and self.saving_process.is_alive():
                    self.saving_process.join()
                self.saving_process = AudioSaveHandler(
                    saving_location=rf'{self.saving_location.value}_mic{self.device_id}.wav',
                    nchannels=1,
                    sample_width=self.pa.get_sample_size(pyaudio.paInt32),
                    frame_rate=384000,
                    record=self.buffer)
                self.saving_process.start()
                # print(len(self.buffer))
                self.buffer = []
                self.check_list[self.process_id] = 0
                print(self.check_list)

        self.stream.stop_stream()
        self.stream.close()
        self.pa.terminate()

        if self.saving_process and self.saving_process.is_alive():
            self.saving_process.join()


class Application:
    def __init__(self, alive_flag, window, current_output, process_names):
        self.alive_flag = alive_flag
        self.window = window
        self.window.resizable(0, 0)
        self.current_output = current_output
        self.process_names = process_names

        self.cams = [(process_id, name) for process_id, name in enumerate(self.process_names) if 'cam' in name]
        self.cam_labels = []
        self.mini_size = (190, 150)
        self.selected_cam = None
        self.selected_cam_frame = None
        self.selected_cam_label = None

        self.last_frame = time.perf_counter()

        self.create_widgets()
        self.alive_flag.wait()
        self.update()
        self.window.mainloop()

    def create_widgets(self):
        for process_id, cam in self.cams:
            frame = tk.Frame(master=self.window, width=self.mini_size[0], height=self.mini_size[1])
            frame.grid_propagate(False)
            frame.grid(row=0, column=process_id)

            label = tk.Label(master=frame, bg='black', borderwidth=2)
            label.bind("<Button-1>", lambda e, x=process_id: self.select_window(x))
            label.pack(fill=tk.BOTH)
            self.cam_labels.append(label)

            new_frame = tk.Frame(master=frame)
            new_frame.place(x=2, y=2, anchor=tk.NW)
            tk.Label(master=new_frame, text=cam, bg='black', fg='white', font=("Helvetica", 16)).pack()

            self.selected_cam_frame = tk.Label(master=self.window, width=self.mini_size[0] * 3,
                                               height=self.mini_size[1] * 3, bd=-2)
            self.selected_cam_frame.grid(row=1, column=0, columnspan=3)
            self.selected_cam_frame.grid_remove()

            self.selected_cam_label = tk.Label(master=self.selected_cam_frame, bg='yellow', borderwidth=2)
            self.selected_cam_label.pack(fill=tk.BOTH)

    def update(self):
        for process_id, cam in self.cams:
            if self.current_output[process_id] is not None:
                image = Image.fromarray(self.current_output[process_id])
                image = ImageTk.PhotoImage(image.resize((self.mini_size[0], self.mini_size[1]), Image.ANTIALIAS))
                self.cam_labels[process_id].config(image=image)
                self.cam_labels[process_id].image = image

        if self.selected_cam is not None:
            if self.current_output[self.selected_cam] is not None:
                image = Image.fromarray(self.current_output[self.selected_cam])
                image = ImageTk.PhotoImage(
                    image.resize((self.mini_size[0] * 3 + 8, self.mini_size[1] * 3 + 8), Image.ANTIALIAS))
                self.selected_cam_label.config(image=image)
                self.selected_cam_label.image = image

        if self.alive_flag.is_set():
            this_frame = time.perf_counter()
            # print(f'FPS: {1 / (this_frame - self.last_frame)}')
            self.last_frame = this_frame
            self.window.after(30, self.update)
        else:
            self.window.quit()

    def select_window(self, clicked_cam):
        if self.selected_cam == clicked_cam:
            self.cam_labels[clicked_cam].config(bg='black')
            self.selected_cam = None
            self.selected_cam_frame.grid_remove()
        else:
            self.cam_labels[clicked_cam].config(bg='yellow')
            if self.selected_cam is not None:
                self.cam_labels[self.selected_cam].config(bg='black')
            self.selected_cam = clicked_cam
            self.cam_labels[clicked_cam].config(bg='yellow')
            self.selected_cam_frame.grid()


class GUIHandler(Process):
    def __init__(self, alive_flag, current_output, process_names):
        super(GUIHandler, self).__init__()
        self.current_output = current_output
        self.process_names = process_names
        self.alive_flag = alive_flag

    def run(self):
        Application(self.alive_flag, tk.Tk(), self.current_output, self.process_names)


def _create_connection(ip, port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    client_socket.connect((ip, port))
    client_socket.setblocking(False)
    return client_socket


if __name__ == '__main__':
    tlFactory = pylon.TlFactory.GetInstance()
    cameras = tlFactory.EnumerateDevices()

    pa = pyaudio.PyAudio()
    microphones = []
    valid_mics = ['Microphone (UltraMic384K 16bit ']
    for i in range(pa.get_device_count()):
        devinfo = pa.get_device_info_by_index(i)
        for name in valid_mics:
            if name == devinfo['name']:
                microphones.append(i)

    processes = []
    manager = Manager()
    all_alive = manager.Event()
    all_recording = manager.Event()
    check_list = manager.list([1] * (len(cameras) + len(microphones)))
    saving_location = manager.Value(c_wchar_p, r'')
    current_output = manager.list([None] * (len(cameras) + len(microphones)))

    device_meta = {}
    trial_meta = {}

    process_id = 0
    process_names = []
    for device_id, device in enumerate(cameras):
        trial_meta[f'cam{device_id}'] = manager.dict()

        p = BaslerVideoHandlerProcessTriggered(process_id, all_alive, all_recording, check_list, saving_location,
                                               trial_meta[f'cam{device_id}'], current_output, device_id)
        p.start()
        processes.append(p)
        process_names.append(f'cam{device_id}')
        process_id += 1

    for device_id in microphones:
        trial_meta[f'mic{device_id}'] = manager.dict()

        p = AudioHandlerProcess(process_id, all_alive, all_recording, check_list, saving_location,
                                trial_meta[f'mic{device_id}'], current_output, device_id)
        p.start()
        processes.append(p)
        process_names.append(f'mic{device_id}')
        process_id += 1

    p = GUIHandler(all_alive, current_output, process_names)
    p.daemon = True
    p.start()
    processes.append(p)

    def saving():
        check_list[:] = [1] * len(check_list)

    def set_location(location):
        folder, file_prefix = location.rsplit('\\', 1)
        if not os.path.exists(folder):
            os.makedirs(folder)
        saving_location.value = location

    command_dict = {
        '1': all_recording.set,
        '2': all_recording.clear,
        '3': saving,
        '4': all_alive.clear,
        'set_location': set_location,
    }

    client_socket = _create_connection('localhost', 30000)

    while sum(check_list) != 0:
        time.sleep(0.1)
    all_alive.set()
    client_socket.send(b'1')

    while True:
        # inbound communication
        ready_to_read, _, _ = select.select([client_socket], [], [], 0.5)
        if len(ready_to_read) > 0:
            dataFromClient = ''
            while True:
                data = client_socket.recv(1).decode()
                if data == '|':
                    break
                dataFromClient += data
            message = dataFromClient.split(' ', 1)
            print(message)
            if len(message) > 1:
                command_dict[message[0]](*message[1:])
            else:
                command_dict[message[0]]()

        if sum(check_list) != 0:
            while sum(check_list) != 0:
                time.sleep(0.1)
            with open(rf'{saving_location.value}_meta.json', 'w') as outfile:
                copy_of_trial_meta = trial_meta.copy()
                for key in copy_of_trial_meta.keys():
                    copy_of_trial_meta[key] = dict(copy_of_trial_meta[key])
                    trial_meta[key].clear()
                json.dump(copy_of_trial_meta, outfile)
            client_socket.send(b'1')

        if not all_alive.is_set():
            for process in processes:
                process.join()
            location_split = saving_location.value.rsplit('\\', 3)
            location = location_split[0] + '\\' + location_split[1] + '\\' + location_split[1]
            with open(rf'{location}_meta.json', 'w') as outfile:
                json.dump(device_meta, outfile)
            client_socket.send(b'1')
            break
