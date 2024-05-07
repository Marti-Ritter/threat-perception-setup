from multiprocessing import Process, Manager
import tkinter as tk
from PIL import Image, ImageTk
import numpy as np
import time


class Application:
    """ GUI """

    def __init__(self, alive_flag, window, device_dict):
        self.alive_flag = alive_flag
        self.window = window
        self.device_dict = device_dict

        self.cams = self.device_dict.keys()
        self.cam_labels = []
        self.mini_size = (600, 400)
        self.resize_factors = []

        self.last_frame = time.perf_counter()

        self.create_widgets()
        self.update()
        self.window.mainloop()

    def create_widgets(self):
        """Create button. """
        colors = ['red', 'blue', 'yellow']
        for i, cam in enumerate(self.cams):
            label = tk.Label(master=self.window, width=self.mini_size[0], height=self.mini_size[1], bg=colors[i])
            label.pack(fill=tk.Y, side=tk.LEFT)
            self.cam_labels.append(label)
            size = self.device_dict[cam]['current_frame'].shape[::-1]
            self.resize_factors.append((self.mini_size[0] / size[0], self.mini_size[1] / size[1]))

    def update(self):
        for i, cam in enumerate(self.cams):
            img = Image.fromarray(np.uint8(self.device_dict[cam]['current_frame']))
            img = ImageTk.PhotoImage(img.resize((int(img.width * self.resize_factors[i][0]),
                                                 int(img.height * self.resize_factors[i][1])), Image.ANTIALIAS))
            self.cam_labels[i].config(image=img)
            self.cam_labels[i].image = img

        if self.alive_flag.is_set():
            this_frame = time.perf_counter()
            print(f'FPS: {1 / (this_frame - self.last_frame)}')
            self.last_frame = this_frame
            self.window.after(30, self.update)


class GUIHandler(Process):
    def __init__(self, alive_flag, device_dict):
        super().__init__()
        self.device_dict = device_dict
        self.alive_flag = alive_flag

    def run(self):
        Application(self.alive_flag, tk.Tk(), self.device_dict)


class WhiteNoiseProcess(Process):
    def __init__(self, alive_flag, my_dict):
        super().__init__()
        self.alive_flag = alive_flag
        self.my_dict = my_dict

    def run(self):
        self.alive_flag.wait()

        while self.alive_flag.is_set():
            white_noise = np.random.rand(800, 1200) * 255
            self.my_dict['current_frame'] = white_noise


if __name__ == '__main__':
    manager = Manager()
    all_alive = manager.Event()
    meta = {
        'devices': {
            'device0': manager.dict({
                'meta': None,
                'current_frame': None
            }),
            'device1': manager.dict({
                'meta': None,
                'current_frame': None
            }),
            'device2': manager.dict({
                'meta': None,
                'current_frame': None
            })
        },
    }
    processes = []

    for i in range(3):
        p = WhiteNoiseProcess(all_alive, meta['devices'][f'device{i}'])
        p.daemon = True
        p.start()
        processes.append(p)

    time.sleep(2)
    all_alive.set()

    GUIProcess = GUIHandler(all_alive, meta['devices'])
    GUIProcess.daemon = True
    GUIProcess.start()

    time.sleep(50)
    all_alive.clear()

    for i, process in enumerate(processes):
        process.join()

# Speed: https://python-forum.io/Thread-Tkinter-createing-a-tkinter-photoimage-from-array-in-python3